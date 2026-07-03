# Advisory Board — Final Consensus
v1.14 p3 live progress pr review
Board: Claude (Architecture & systems/claude-opus-4-8) · Codex (Implementation & testing/gpt-5.5). Rounds: 2.

## Verdict: SHIP — unanimous (high confidence)

## Delta vs the previous run
Revises: ~/.advisory-board/runs/v1-14-p3-live-progress-pr-review-2026-07-02 (2026-07-02)
**Trajectory: SHIP WITH CHANGES → SHIP**
Cleared blockers (2):
- Artifact tree advertises status.json/status.html unconditionally — the dry-run preview lies under --no-live-status
- RH-1 docs claim an egress-refused run 'leaves no out dir', but the code (and an existing test) write refusal artifacts
Cleared concerns (4):
- No finalizer stamps an interrupted run — a crash after activate() leaves a live page refreshing on a dead process
- Fixed tempfile name is safe only under the tracker lock
- elapsed_s wall-clock value is a latent golden-test nondeterminism risk
- 'retry' is in the documented status vocabulary but is never emitted
New concerns (5):
- `retry`/`skipped` states are documented but never emitted
- Atomic-write docs overstate `.tmp` cleanup on failure
- Abort guard degrades a forgotten `finish()` into a silent mislabel
- Cross-seat event order is scheduler-dependent — guardrail to preserve
- Best-effort terminal write can leave stale on-disk live status

## What the board couldn't verify
- Neither seat executed the test suite — both reviewed read-only (Codex's sandbox could not even complete `git status` due to temp-cache permission errors). The claimed 1426 passing count rests on the author's and an independent finder's attestation, corroborated by Claude's arithmetic (1404 baseline + 22 new = 1426; 1419 + 7 revision-tests = 1426), not on an executed run.
- Claude accepts that no CLI surface reads `status.json` but did not exhaustively grep the whole tree for a reader; the reader-hardening (TestStatusReaderHardening) makes this moot even if one were added later.

## Open questions
- Trim `retry`/`skipped` from the emitted-state vocabulary now, or footnote them as reserved-not-emitted in the CHANGELOG? Claude does not block either way but wants the CHANGELOG's 'vocabulary' line to stop implying all six states fire.

## Next actions
- Before merge (required per Claude): run `-k Status` plus a full-suite pass; confirm 1426 green and one live-vs-`--no-live-status` artifact diff showing record artifacts byte-identical with only `status.*` differing.
- Run clean normal-path smokes for `--synthesize` and `--output revised-draft` and confirm the outcome is not `interrupted` (Codex).
- Run the focused status tests: TestStatusModuleUnit, TestStatusHtmlRender, TestStatusLiveViewE2E, TestStatusAbortGuardE2E, TestStatusReaderHardening (Codex).
- Merge — both seats consider it mergeable as-is.
- Optional follow-up (this PR or fast-follow): add a positive abort-outcome E2E asserting a clean `--synthesize` and `--output revised-draft` run ends with a success outcome (`ok`/`rounds-complete`), not `interrupted` — Claude's highest-value follow-up.
- Optional: soften the `_atomic_write_text` docstring / CHANGELOG 'on any failure' wording to 'any Python-level failure.'
- Optional: trim `retry`/`skipped` from the emitted vocabulary or footnote them as reserved-not-emitted in the CHANGELOG.
- Release v1.14.0 one phase later, per the release train.

---
_Evidence status is a resolution check — it confirms the cited line exists or the quote is present in the captured material. It does not prove the inference drawn from it is sound (design §9)._
