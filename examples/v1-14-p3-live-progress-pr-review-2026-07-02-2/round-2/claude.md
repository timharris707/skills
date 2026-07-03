I've now verified every resolution against the working-tree source. Producing my round-2 review below. (This is a read-only review task; per the board instructions the review text itself is the deliverable, so I'm not writing a plan file or calling ExitPlanMode.)

---

# Claude seat — round 2 (Architecture & systems)

I re-verified all four resolutions against the working-tree source (not the diff), and this round I traced **every** return path in the post-activate body — the one thing codex and I both flagged as the structural risk. It holds. I'm holding my round-1 SHIP and raising confidence.

## 1. Updated verdict

**SHIP** — confidence **high** on the resolutions (each verified against source, including an exhaustive return-path trace of the abort guard), **medium-high** overall. **What would change it:** a full-suite run coming back below 1426 green, or a clean `--synthesize` / `--output revised-draft` run stamping `interrupted` — I proved the latter can't happen today by inspection (every return path stamps `finish()` first), but I did not execute the suite (read-only), so the green count still rests on the author's + independent finder's attestation, corroborated by the arithmetic (1404 baseline + 22 new = 1426; 1419 + 7 revision-tests = 1426).

## 2. Where I changed my mind / where I still dissent

- **Changed:** nothing in my *verdict* (ship → ship). What moved is my **confidence on the abort guard**, and it moved toward **codex's** framing. Codex's round-1 objection was structural — *"`_execute_run()` now relies on every normal return path in `_run_after_activate()` and its synthesis/revision callees stamping a terminal status before returning."* In round 1 I recorded O3 as "resolved per diff"; this round I discharged codex's concern by reading all seven return sites. They all stamp: `cli.py:449→455`, `571→576`, `596→608`, `704→710`, `732→749/750`, `1094→1095`, `1125→1136/1137`. So codex's worry is a real *maintainability* hazard for future edits — not a current defect. That verification is my own; codex named the shape but the check is independent, so I still call this **independent** (I held my prior view and confirmed it).
- **Still dissent (unchanged from round 1, non-blocking):** the `retry` — and `skipped` — states are advertised vocabulary that the conductor never emits. Confirmed: `rounds.py:261` maps outcomes to `"done"`/`"dropped"` only, and the grep shows *no* emitter of `retry`/`skipped` anywhere; they live solely in `status.py`'s tables (`STATES:83`, glyphs `310–311`, classes `371–372`, labels `380–381`) and the dead `terminal_line` branch (`332–333`). The revision made this an *explicit deferral* (comment at `rounds.py:257–260`), which is honest. I don't block on it, but the CHANGELOG's "`state` vocabulary is …/`retry`/`skipped`" reads as if all six fire.

No dissent against either seat's verdict.

## 3. Strongest remaining objections

All minor; none blocking.

1. **The abort guard degrades a forgotten `finish()` into a *mislabel*, not a loud failure (codex's structural point).** Today every path stamps. But a future return added to `_run_after_activate`/synthesis/revision that forgets `finish()` will come back stamped `interrupted` on a *successful* run — a silent wrong badge, not a crash. Cheapest guard: one positive E2E asserting a clean `--synthesize` (and `--output revised-draft`) run ends with a success outcome (`ok`/`rounds-complete`), *not* `interrupted`. The current `TestStatusAbortGuardE2E` only pins the two *abnormal* paths; `test_run_writes_status_json_and_html` asserts `finished is not None` but never asserts `outcome`. This is the single highest-value follow-up.
2. **`_atomic_write_text` docstring overstates "no `.tmp` … litters" (codex's nit — confirmed).** `status.py:92–93` says the temp is removed "on any failure." True only for *Python-level* exceptions (the `except` at `103–108`); a SIGKILL between `open(tmp)` and `os.replace` leaves `.status.json.tmp`. Mitigating: the tmp name is **fixed**, so the next event's `open(tmp,"w")` truncates and `os.replace` consumes it — self-healing on the next write; residue only survives if the run is killed and never resumes. Behavior is fine; the word "any" should be "any Python-level."
3. **`events[]` cross-seat order is nondeterministic under the real parallel executor** (my round-1 latent note, still latent and correctly handled). The `running`/`done` interleave across seats depends on thread scheduling. The golden dodges this correctly — the event-sequence assertion is single-threaded/serial, and the E2E uses membership (`assertIn`), not full order. Guardrail: the golden must **never** assert full cross-seat ordering. No code change needed.

## 4. Recommended execution sequence

1. **Before merge (required):** run `-k Status` plus a full pass; confirm 1426 green and one live-vs-`--no-live-status` artifact diff (record artifacts byte-identical, only `status.*` differ). This is the one thing I could not execute.
2. **Merge** — mergeable as-is.
3. **Optional, this PR or a fast follow:** add the positive abort-outcome E2E (#3.1); soften the `.tmp` docstring (#3.2); either trim `retry`/`skipped` from the emitted vocabulary or footnote them as reserved-not-emitted in the CHANGELOG (#2).
4. v1.14.0 release one phase later, per the train.

## 5. Invariants and guardrails

- **RH-1 (no `status.*` before egress approval): HOLDS.** `activate()` is the only thing that flips `_active` (`status.py:180–189`), reached solely at `cli.py:397`, *after* the egress gate and `write_pre_spawn_artifacts`. Every pre-activate `_write_files` is a no-op (`status.py:275–276`). The NO-GO (`cli.py:360`) and egress-refusal (`cli.py:387`) `finish()` calls only mutate the in-memory doc + print, then `die()` raises *before* the `try` at `408` — so no dir, no `status.*`. Locked by `test_no_go_preflight_leaves_no_status` and `test_egress_refused_writes_manifest_but_no_status`.
- **Abort guard placement: TIGHT.** Nothing between `activate()` (397) and the `try` (408) can raise, and the `finally` wraps the entire post-activate body — so any abnormal exit after the view hits disk lands in `finish_if_unfinished` (`status.py:232–246`), which is idempotent under lock and leaves seats' last-known states untouched. Original exit code / `die()` message re-raise untouched (`cli.py:412–418`; `except Exception` around the stamp can't swallow `SystemExit`/`KeyboardInterrupt`).
- **Thread-safety: HOLDS.** `_seat_cb` → `tracker.seat` fires from `ThreadPoolExecutor` workers (`rounds.py:266–271`) and serializes on `self._lock`; `round_started`/`round_done`/`activate` run on the main thread outside the fan-out window. Atomic write + fixed tmp name is safe because only one thread writes at a time.
- **Best-effort isolation: HOLDS.** `_write_files` swallows + warns-once (`status.py:283–289`); `_notify` swallows a bad callback (`rounds.py:249–250`); `_print_line` swallows print errors (`297–298`). A live-view failure cannot take the run down.
- **Byte-identical record artifacts under `--no-live-status`: HOLDS** — `NullTracker` (`status.py:111–125`) is a pure no-op; `live_status` is the single source of truth for both the wiring and `render_artifact_tree` (`artifacts.py:319`).

## 6. Risks, stale assumptions, missing evidence

- **Missing evidence:** the 1426 green count is attested, not executed by me (read-only) — the one open verification, same caveat as round 1.
- **"No CLI surface reads `status.json`":** I accept this (the module is conductor-write-only; `event_tuples`/`render_status_html` callers are the tracker + tests), but I did not exhaustively grep for a reader across the whole tree. The hardening (`TestStatusReaderHardening`) makes the point moot even if one were added later — the readers can't traceback on a malformed doc.
- **Stale-doc risk:** the `retry`/`skipped` vocabulary and the "no `.tmp`" absolute are the two spots where docs are a hair ahead of behavior. Cosmetic.

## 7. Concrete evidence

- **Blocker 1 cleared:** `config.py:119` `live_status: bool = True`; `config.py:797` `live_status=not getattr(args, "no_live_status", False)`; `artifacts.py:319` `if config.live_status:` gates the status line — every sibling optional slot is gated the same way. Locked by `test_artifact_tree_omits_status_when_no_live_status` + `test_dry_run_no_live_status_omits_status_from_preview`.
- **Blocker 2 cleared:** the RH-1 prose now reads "an egress-refused run writes only the refusal manifest (`egress-manifest.md` + `sensitivity.json`), never `status.*`" at `status.py:34–37`, the SKILL.md "How A Run Executes" paragraph, the `scripts/README.md` `status.py` row, and the CHANGELOG bullet. Behavior unchanged; `test_egress_refused_writes_manifest_but_no_status` locks manifest-present / `status.*`-absent.
- **Codex ship-gate (malformed readers) cleared:** `event_tuples` isinstance-guards doc/events/entry (`status.py:352–358`); `render_status_html` normalizes a non-dict doc (`408–409`), non-dict `seats` (`417–418`), corrupt seat entry (`434–435`), non-list `events` (`454–456`). `TestStatusReaderHardening` proves no raw traceback.
- **O3 abort-refresh cleared:** try/finally at `cli.py:408–418`; `finish_if_unfinished` at `status.py:232–246`; `OUTCOME_INTERRUPTED` renders `drop` + drops the meta-refresh (`status.py:79`, `render_status_html:420–429`). `TestStatusAbortGuardE2E` covers the mid-fan-out `die()` (exit code + message preserved) and the `KeyboardInterrupt` (re-raised).
- **Dead vocabulary (my dissent):** `rounds.py:253,261–262` emit only `"running"`/`"done"`/`"dropped"`; grep confirms no `retry`/`skipped` emitter outside `status.py`'s static tables.

## Challenges to the board

- **Codex (correctness/security):** I discharged your round-1 structural objection by tracing all seven post-activate return paths — they all stamp `finish()` before returning, so the guard's `interrupted` net never mislabels a current success path. Please convert that from "checked visible paths" to a **regression lock**: one positive E2E that a clean `--synthesize` and a clean `--output revised-draft` run end with a success outcome, not `interrupted`. And confirm you concur the `.tmp` "on any failure" wording is a doc-only softening (fixed tmp name ⇒ self-healing), not a behavioral fix.
- **To both:** do we trim `retry`/`skipped` from the emitted-state vocabulary now, or footnote them as reserved-not-emitted? I don't block either way — I want the CHANGELOG's "vocabulary" line to stop implying all six fire.

BASIS: independent
VERDICT: ship
