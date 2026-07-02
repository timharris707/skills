# Changes Schema — `changes.json`

When you run a board with `--output revised-draft` (v1.13), the conductor — after synthesis has
produced a validated `verdict.json` — spawns a **revision seat** to produce a board-derived,
findings-mapped **revised copy of the source**, each edit mapped by the model to the finding it
resolves, mechanically validated (coverage reconciliation + index/title cross-assert). (It is a
*findings-mapped revision*, not yet *board-endorsed*: the per-edit endorsement pass — where the non-revision
seats vote ENDORSE/OBJECT/ABSTAIN on each edit — lands in v1.13 P4. Until then `endorsements` is
empty and the draft is derived from the board's findings, not voted on.) That produces three
artifacts in the run dir:

- **`revised-draft.md`** (prose) or **`revised-draft.<orig-ext>`** (code) — the revised source,
  **byte-clean**: the revised bytes and nothing else, no metadata header of any kind (a header
  would corrupt code the moment it is saved). Applying it is *your* act — the source file is
  never written (D6).
- **`changes.json`** — the machine-readable **edit → finding mapping**, the artifact of record.
- **`revision/<seat>.md`** + **`revision/<seat>.raw`** — the black-box record of the spawn
  (mirrors `synthesizer/`).

`verdict.json` gains a tiny tool-authored pointer at `changes = {artifact, sha256}` binding the
verdict to this file's bytes (see `references/verdict-schema.md`). The two together prove a
findings-mapped revision existed for that verdict and pin its exact bytes (per-edit *endorsement*
is the later P4 pass).

## Schema (`advisory-board/changes@1`)

```json
{
  "schema": "advisory-board/changes@1",
  "title": "Payments API idempotency keys",
  "source": { "name": "plan.md", "sha256": "4a6a…64 hex… (sha256 of the source's UTF-8 text as read, LF-normalized)" },
  "revised": { "artifact": "revised-draft.md", "sha256": "7442…64 hex… (the revised bytes ON DISK)" },
  "source_type": "prose",
  "revision_seat": "claude",
  "edits": [
    {
      "n": 1,
      "locator": { "kind": "lines", "from": 41, "to": 58 },
      "summary": "Tighten the refund-window claim to the contractually supported 30 days.",
      "resolves": [ { "list": "blockers", "index": 0, "title": "Refund window overstated" } ],
      "status": "applied"
    },
    {
      "n": 2,
      "locator": { "kind": "insert-after", "line": 0 },
      "summary": "Add a reserve-before-charge invariant note at the top.",
      "resolves": [ { "list": "concerns", "index": 0, "title": "24h TTL is an undocumented client contract" } ],
      "status": "applied"
    }
  ],
  "unresolved": [
    {
      "findings": [
        { "list": "blockers", "index": 1, "title": "Commit to the 30-day window" },
        { "list": "concerns", "index": 0, "title": "Remove the window entirely" }
      ],
      "reason": "conflict: the two findings demand incompatible edits",
      "note": "One finding wants a firm 30-day commitment; the other wants the window removed. Both cannot be satisfied in one draft; left for a human to reconcile."
    }
  ],
  "endorsements": []
}
```

### Fields

Everything structural is **conductor-computed** — the model authors only `summary`, `resolves`,
and (on an `unresolved` entry) `reason`/`note`; the conductor computes `n`, `status`, the shas,
`source_type`, `revision_seat`, `title`, and the empty `endorsements` list.

- `schema` — always `advisory-board/changes@1`.
- `title` — the run title (same one the verdict and other artifacts carry).
- `source` — `{name, sha256}`: the source's basename and the sha256 of the source's **UTF-8 text
  as read** — universal-newline (LF-normalized) — the same value the run recipe and the egress
  records bind, so the three agree exactly. This is *not* a hash of the untouched on-disk bytes:
  the source is read with universal-newline translation, so a CRLF file hashes as its LF form. The
  revision path refuses a CR/CRLF source up front for exactly this reason (the whole pipeline is
  LF-normalized end to end and would otherwise ship a re-terminated draft mislabeled byte-clean),
  so on the revision path the source *is* LF and this sha equals its on-disk bytes. **Caveat:** a
  stdin source is consumed before any raw sniff is possible, so it cannot be refused for CR the way
  a path source is — pass an LF path source when byte-exact source identity matters.
- `revised` — `{artifact, sha256}`: the revised-draft artifact name and the sha256 of the
  **byte-clean revised bytes on disk**. This sha256 equals `revised-draft.*` exactly — a header
  or trailing metadata would break the identity, which is why the draft carries none.
- `source_type` — `prose` | `code`. Resolved at run time from `--source-type` or the extension
  heuristic; drives the redline format (P3: word-level `<ins>/<del>` for prose, a unified
  `.patch` for code).
- `revision_seat` — the board seat whose CLI/adapter produced the revision.
- `edits[]` — the applied edits, in edit order:
  - `n` — 1-based, dense, in edit order (conductor-assigned).
  - `locator` — where the edit changed the **original** source. Two shapes:
    - `{ "kind": "lines", "from": N, "to": M }` — a **1-based inclusive** line range in the
      original source (`from <= to`, within the source).
    - `{ "kind": "insert-after", "line": N }` — a pure insertion after original line `N`
      (`N = 0` means the top of the file).
  - `summary` — the model's one line on what the edit changed and why.
  - `resolves[]` — the finding(s) this edit resolves, each the composite
    `{list, index, title}` with `list ∈ {blockers, concerns}` and `index` the finding's
    **0-based position within its list** (D9). The conductor **cross-asserts** each ref
    against the verdict before write — the index must be in bounds AND
    `verdict[list][index].title == title` (exact); an out-of-bounds index or an index/title
    mismatch rejects the whole revision. The index pins the finding unambiguously even when
    two findings share a title. (`caveats` are plain strings with no titles, and `dissent`
    is not an editable finding, so neither is resolvable — D9.)
  - `status` — `applied` in `@1`. **Conductor-computed** from the diff reconciliation, never
    taken from the model.
- `unresolved[]` — conflicting findings the revision seat could not satisfy together (D14). Each
  entry names the `findings[]` in tension (same `{list, index, title}` composite,
  cross-asserted), a `reason`, and a one-paragraph `note`. Legitimate output, surfaced loudly
  (the run card prints the count) — a non-empty `unresolved` **never** moves the exit code.
- `endorsements[]` — empty in P2; filled by the endorsement pass (v1.13 P4) with
  `{seat, edit_n, position, note}` rows.

### What the conductor mechanically checks (never model-asserted)

The revision seat *reasons* the edits and the revised text; the conductor *verifies* every claim
in code before it writes anything (§11):

1. **Cross-assert** — every `resolves`/`findings` ref must name a real verdict finding by its
   full `{list, index, title}` composite: the `index` is bounds-checked and
   `verdict[list][index].title == title` (exact), `list ∈ {blockers, concerns}`. An
   out-of-bounds index or an index/title mismatch rejects (the message lists the valid refs).
   A duplicate title among the verdict's resolvable findings still refuses the revision up front
   as defense in depth — the index pins each ref, but a duplicate title is ambiguous to a human
   reader and none is present to disambiguate (D9).
2. **INV-1 reconciliation** — `difflib.SequenceMatcher(...).get_opcodes()` over the original vs
   the revised lines. Every non-equal opcode region must be claimed by ≥1 edit locator, and every
   edit locator must overlap ≥1 non-equal region (an `insert-after` anchor must sit at a real
   insertion point). Any discrepancy rejects.

   > **Canonical-boundary rule (a determinism trade).** The diff is what defines a change, so a
   > locator reconciles against difflib's *canonical* opcode boundaries. An ambiguous insertion —
   > e.g. duplicating a line adjacent to an identical one — has exactly ONE canonical boundary
   > under difflib. A model that names an equally-valid alternate boundary (a semantically
   > identical result, but a different anchor) reconciles against no hunk there and **rejects
   > safely**: the reject is loud and the correct boundary is recoverable from the diff, so the
   > trade is a rare false-reject in exchange for a fully deterministic, non-heuristic check.
3. **Completeness** — every verdict **blocker** must appear in some edit's `resolves[]` **or** in
   an `unresolved[]` entry; concerns are best-effort (no check).
4. **`status`/`n`/shas** are computed from the reconciliation and the bytes on disk — never read
   from the model.

Anything that fails takes the **reject path**: `revised-draft-rejected.*` + `changes-rejected.json`
+ a loud warning + exit `0` (`--strict-exit` → exit `4`). A revision failure never discards the
completed rounds or the verdict.

## Validating a `changes.json`

`scripts/board_changes.py` validates the schema (strict — unknown top-level keys refused, exact
field types, locator shape checks, `resolves`-list enum {blockers, concerns}). The conductor runs
it before writing; you can run it by hand:

```
python3 scripts/board_changes.py changes.json          # validate + summary
python3 scripts/board_changes.py changes.json --json    # echo normalized JSON
```

A schema violation exits `2`, the same clean-`die()` convention as `board_verdict.py`.
