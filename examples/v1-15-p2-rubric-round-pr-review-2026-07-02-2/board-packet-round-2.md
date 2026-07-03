# Board packet — round 2 (cross-reading: summaries — structured digest)

## Where the board stands after round 1

Verdicts: claude=caution · codex=block
Agreement: split — 1×caution, 1×block
Shared evidence (raised by ≥2 seats): `--rubric`, `rubric-rejected.json`, `rubric.json`

## By topic

### Verdict

- **claude:** **CAUTION — proceed only with the egress and schema-hygiene fixes below.** Confidence: **high.** The settled design (D15/D16/D18/D20) is faithfully and, in most places, impressively implemented: the mechanical partition reconciliation, the …
- **codex:** Block, high confidence. I would change this to caution once the rubric proposal prompts are hash-bound in the egress packet and chair mechanical invalid replies retry once before refusal.

### Strongest objections

- **claude:** **① Undisclosed pre-round egress (concern — consent surface).** The `--rubric` pass egresses the **full source to every board seat before round 1**, but the disclosure the user approves is not updated to say so. Confirmed by inspection: …
- **codex:** - `scripts/_conductor/egress.py:95-111`, `scripts/_conductor/cli.py:287-288`, `scripts/_conductor/cli.py:673-688` — blocker: rubric proposal prompts are spawned outside the approved packet hash. `build_packet()` only builds round-1 …

### Recommended execution sequence

- **claude:** 1. **Egress first (①②).** Add the rubric purpose mention to `disclosure_line()`; add an approved-content-hash re-assertion to the rubric fan-out mirroring round-1. Re-run the consent/egress tests; add one asserting the disclosure names the …
- **codex:** 1. Fix egress first: prebuild rubric proposal `PacketBlob`s before approval, list them in the manifest, include them in the approved hash discipline, write them before spawn, and reassert their hash at rubric spawn time. 2. Move chair …

### Invariants & guardrails

- **claude:** - **Consent precedes every egress, and the disclosure names every egress purpose.** The rubric leg is a new egress *event* (N seats, pre-round) even at the same byte/provider category — the consent UX must reflect it, and each egress …
- **codex:** Every spawned prompt that can leave the machine must be in a consented packet hash. Rubric must run after egress approval and before round 1. No round artifacts or verdict may exist after rubric refusal. Proposal IDs stay conductor-minted, …

### Risks, stale assumptions & missing evidence

- **claude:** - **Stale assumption:** "same source, same providers ⇒ no disclosure needed." The PR's own CHANGELOG contradicts it (it intended a purpose mention). Resolve the policy, then make code match. - **Stale assumption:** "source is immutable …
- **codex:** The “no new consent category” claim is not enough for hash-bound consent; exact outbound bytes matter. The reported 1484 OK suite does not prove the egress invariant because tests check artifact existence, not approval packet membership. …

### Concrete evidence

- **claude:** - **CHANGELOG overclaim (①):** `CHANGELOG.md` (diff) — *"no new consent category (the disclosure text gains a purpose mention only)."* No disclosure code appears anywhere in the diff; `egress.disclosure_line()` has no rubric mention …
- **codex:** `write_pre_spawn_artifacts()` says it persists “the APPROVED packet” before spawn and writes only `blobs` at `scripts/_conductor/artifacts.py:716-744`; rubric prompt files are instead written after `run_rubric_proposals()` returns at …

### Challenges to the board

- **claude:** - **Codex (systems/egress):** Is a pre-round full-source egress genuinely covered by the existing run disclosure, or must `disclosure_line()` name it? This is a consent-policy call, not a code call — I want a second opinion before we treat …
- **codex:** Ask security to attack the egress hash model. Ask correctness to challenge retry classification for model-authored structural failures versus conductor internal errors. Ask test strategy to add non-deterministic/default-chair replay cases. …
