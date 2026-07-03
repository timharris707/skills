# Advisory Board — Final Consensus
v1.14 p3 live progress pr review
Board: Claude (Architecture & systems/claude-opus-4-8) · Codex (Implementation & testing/gpt-5.5). Rounds: 2.

## Verdict: SHIP WITH CHANGES — unanimous (high confidence)

## Consensus blockers (must fix before ship)
1. Artifact tree advertises status.json/status.html unconditionally — the dry-run preview lies under --no-live-status — Both seats make this the primary defect. render_artifact_tree appends the status line with no config guard, while every sibling optional slot in the same function is gated (grounding, echo-score, synthesizer, revised-draft, endorsement). Because the tree is printed inside the dry-run preview ('=== artifact tree it WOULD create ==='), `run --dry-run --no-live-status` promises status.json/status.html that the real run never writes — Claude calls this a lie in the preview, Codex an opt-out that lies in the artifact preview. RunConfig has no live_status field; the only no_live_status signal lives on args (cli.py:328), so render_artifact_tree(config) cannot currently gate the line. Impact is real but bounded — no byte-pinned golden of the full tree exists, so the suite stays green (an output-honesty bug, not a red test).
   - evidence: `scripts/_conductor/artifacts.py:309` (code) — unchecked
   - evidence: `scripts/_conductor/cli.py:285` (code) — unchecked
   - evidence: `tests/test_run_board.py:7259` (code) — unchecked
   - evidence: scripts/_conductor/artifacts.py — “so the tree stays truthful about what a --no-endorse run ...” (source) — unchecked
   - evidence: `scripts/_conductor/cli.py:328` (code) — unchecked
2. RH-1 docs claim an egress-refused run 'leaves no out dir', but the code (and an existing test) write refusal artifacts — Both seats confirm the egress-refused path calls os.makedirs(config.out_dir) and writes egress-manifest.md + sensitivity.json before dying, and an existing test asserts exactly that. The status behavior is correct — tracker.finish() fires while the tracker is still inactive (activate() runs only on the approved path at cli.py:396), so _write_files early-returns on not self._active and no status.* lands. But the CHANGELOG/SKILL/README/status.py prose says a refused run 'leaves no out dir — and no status.*'; only the status.* half is true. Claude notes the fix is documentation only (reword to 'preflight NO-GO leaves no dir; egress-refused writes only the refusal manifest, never status.*'); Codex frames it as an internal inconsistency to resolve.
   - evidence: `scripts/_conductor/cli.py:377` (code) — unchecked
   - evidence: `tests/test_run_board.py:795` (code) — unchecked
   - evidence: CHANGELOG.md — “egress-refused run leaves no out dir” (source) — unchecked
   - evidence: `SKILL.md:145` (code) — unchecked
   - evidence: `scripts/README.md:42` (code) — unchecked

## Hard dissent (preserved)
- Codex: Dissents from stopping at Claude's artifact-tree fix alone: the malformed/corrupted status-reader invariant remains unmet. render_status_html() tolerates missing keys but not malformed container types — seats.items() and e.get() (status.py:379-402), and event_tuples() indexing event keys directly (status.py:313-316), can raise AttributeError/KeyError on hand-authored status.json. Codex gates SHIP on this being handled without crashes (skip/exit 2 cleanly); Claude did not raise it.
- Claude: Pushes back on Codex's 'internally inconsistent' framing of RH-1 as a matter of emphasis, not a material disagreement. Claude is precise that the code is correct on the invariant that actually matters (no status.* before hash-bound consent); only the prose overreaches by conflating 'no status.*' with 'no dir'. That distinction makes the fix a one-line doc change rather than a code change, and it should not read as a safety hole.

## What the board couldn't verify
- Neither seat re-ran the test suite in this read-only review; both verified the code claims by reading, not by execution.
- The reported 1419-OK test count and the clean live-vs-opt-out artifact diff were not independently reproduced in this review (Claude).

## Open questions
- RH-1 resolution direction: preserve the existing egress-refusal manifest behavior and reword the docs to 'no status.* before activation/egress approval', or deliberately change the refusal path (and its existing tests) so it writes nothing?
- Should the resolved live_status flag affect only runtime/preview decisions, or also be preserved across recipe replay (Codex)?

## Next actions
- Add a resolved live_status boolean to RunConfig, set from not args.no_live_status (mirroring endorse), as a single source of truth for cli.py:328 and render_artifact_tree(config).
- Gate the status line in render_artifact_tree() (artifacts.py:309) on live_status; add test_artifact_tree_omits_status_when_no_live_status mirroring test_run_board.py:7259, plus a dry-run --no-live-status test asserting no status.json/status.html in the preview.
- Reconcile the RH-1 prose in CHANGELOG.md:28, SKILL.md:145, scripts/README.md:42, and the status.py docstring to 'no status.* before egress approval'; add an egress-refused E2E test asserting status.json/status.html absent (the dir may exist with the refusal manifest).
- Harden render_status_html() and event_tuples() against malformed status.json so hand-authored/corrupt input skips or exits 2 cleanly rather than raising AttributeError/KeyError (Codex).
- Optional (O3): wrap the post-activate() run body so any abnormal exit stamps finished + outcome='interrupted' and re-renders the now-static HTML.
- Re-run -k Status plus the dry-run/run-flow tests and one live-vs-opt-out artifact diff; confirm the count moves 1419→1421 with the two new tests.

---
_Evidence status is a resolution check — it confirms the cited line exists or the quote is present in the captured material. It does not prove the inference drawn from it is sound (design §9)._
