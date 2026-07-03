# Board packet — round 2 (cross-reading: summaries — structured digest)

## Where the board stands after round 1

Verdicts: claude=ship · codex=block
Agreement: split — 1×ship, 1×block
Shared evidence (raised by ≥2 seats): `--revise`, `choose_chair_seat`, `egress_blobs`

## By topic

### Verdict

- **claude:** **SHIP** — confidence: **high.** Both prior blockers are genuinely resolved in the actual working tree (not just claimed in the diff), all four concerns are addressed, and every cross-cutting integration point I was worried about checks …

### Strongest objections

- **claude:** 1. **The partition invariant is implemented twice** — `rubric.py:reconcile_partition` (write-time) and an inline re-check in `board_rubric.validate` (last-gate). They agree today, but they're independent code paths; a future edit to one …

### Recommended execution sequence

- **claude:** This is a review of a completed change, not a build plan, so the sequence is merge-hygiene: 1. **Run the full suite on a clean checkout** and confirm 1499 OK (I trusted the reported count; I did not execute it). This is the one gate I …

### Invariants & guardrails

- **claude:** - **Identity is conductor-owned** (§11): `mint_proposals` is the sole proposal-id source (board order, then within-seat); criterion ids `c1…cN` assigned in `build_rubric`; a model-supplied `id` is dropped at parse …

### Concrete evidence

- **claude:** - Consent-hash fold: `cli.py:299-301`, `egress.py:324`, re-assert `cli.py:714`, round-1 sub-hash `cli.py:416` + `rounds.py:202-203`. - Round-2 precedent legitimizing the chair egress: `egress.py:38-65` (`build_round2` embeds `own_review`), …

### Challenges to the board

- **claude:** - **Codex (adversarial/systems):** Is the single shared workdir across the concurrent proposal fan-out actually safe for *real* CLIs (not just mocks) that may write scratch files into `cwd`? It's consistent with rounds/endorsement, but …

### codex — review (no section headers found; head excerpt)

**Verdict** Block, medium-high confidence. I would change this to caution/ship after the rubric proposal packet is made equivalent to the actual round-1 review context for `--revise` and `--repo`, with tests proving those composed paths. **Strongest Objections** - **BLOCKER: rubric proposals are not built from the same full source packet as round 1.** `cmd_run()` prepares repo grounding and revision context before `_execute_run()` ([cli.py](skills/advisory-board/scripts/_conductor/cli.py:252), [cli.py](skills/advisory-board/scripts/_conductor/cli.py:260)). Round 1 …
