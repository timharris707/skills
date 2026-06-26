# Advisory Board — Final Consensus
how should advisory board respond to openrouter fusion
Board: Claude (Market & user value/claude-opus-4-8) · Codex (Execution & GTM/gpt-5.5) · Gemini (Second-order & risk/gemini-3.5-flash). Rounds: 2.

## Verdict: Proceed with care — unanimous (high confidence)
Workable, but address the flagged concerns before you go ahead.

## Consensus blockers (must fix before ship)
1. Refuse a metered, hosted inline API (the Fusion trap) — All three seats converge that becoming a metered, server-side inline model product would discard the board's structural moats — ~$0 marginal subscription economics, local/private operation, and a gateable abstaining verdict. The single thing to refuse is a hosted, metered advisory-board/fusion-style model id that bypasses local subscriptions, local-only mode, provenance artifacts, or the abstaining gate. Inline escalation should instead be a thin local CLI/MCP wrapper over the existing conductor, not a new hosted API.
   - evidence: SKILL.md — “Use subscription CLIs by default, not provider API keys.” (source) — unchecked
   - evidence: judgment — A hosted metered inline API trades the three structural moats (~$0 marginal, local/private, gateable) for a commodity slot in someone else's gateway — the 'one thing to refuse' named by all three seats.
2. Any inline/escalation mode must preserve egress consent, read-XOR-network, and exit-3 abstain — A local escalation wrapper built to 'feel instant' must not bypass the hash-bound egress/consent gate, the read-XOR-network rule, or the abstain (exit 3) semantics. Gate + --repo already refuses any seat that cannot be de-networked (today gemini, antigravity); the wrapper inherits this unconditionally. An inline 'one-shot board' must also remain a real board of >= 2 seats that actually ran, not a one-seat call dressed as a board.
   - evidence: SKILL.md — “the safety policy is read XOR network … Seats that can't ...” (source) — unchecked
   - evidence: `scripts/_conductor/egress.py:274` (code) — unchecked
   - evidence: `scripts/board_verdict.py:240` (code) — unchecked
   - evidence: `scripts/board_verdict.py:172` (code) — unchecked
3. New structured-output fields must stay informational and never feed the gate — Adding Fusion-style fields (partial_coverage, unique_insights, blind_spots) is endorsed as additive, but the deterministic gate must keep reading each seat's observed final-round verdict and refuted citations, never self-reported confidence or narrative/comparison fields. Any new field that leaks into gate_outcome dilutes the gate's legibility and re-introduces a gameable signal.
   - evidence: `scripts/board_verdict.py:239` (code) — unchecked
   - evidence: references/verdict-schema.md — “confidence — low | medium | high. A self-reported number;...” (source) — unchecked

## Hard dissent (preserved)
- Claude: Ranks positioning (#6) as the first milestone — the precondition for inline landing as a differentiator rather than a me-too — and rejects framing inline as the 'biggest GTM gap versus Fusion.' The local-MCP board is a differentiator to seize (subscription, gate, privacy), not a parity feature to ship; shipping the MCP wrapper without the reframe just produces a worse, free Fusion.
- Codex: Dissents from making positioning alone the next milestone: GTM needs a callable surface so other agents can actually escalate to the board. Holds the local embeddable escalation milestone as the single highest-leverage move, with positioning shipped in the same release. Treats CLI DX as a scoping constraint, not a blocker, since the repo already has preflight, timeouts, failure classification, and --synthesize.
- Gemini: Dissents from making inline escalation (#1) the immediate priority: positioning (#6) and crisper structured output (#4) must precede it, because background auth hangs and minutes-long multi-round local runs make an inline IDE tool fragile. Conditionally supports only a local-only CLI/MCP bridge over already-authenticated user CLIs in a later milestone, and completely rejects any metered hosted gateway.

## What the board couldn't verify
- Fusion's public claims (one API call, 1–8 models, judge JSON, pass-through pricing, '+6.7 from 2×Opus' / DRACO-style results) are packet-only and could not be checked against the tree in this read-only review.
- There is no verified benchmark in the repository proving that multi-round cross-reading debate beats a judge/synthesis-only panel; 'debate beats solo/compare' remains a positioning hypothesis until measured.
- It could not be verified from this read which Gemini model id is canonical (SKILL.md text vs registry default).

## Open questions
- Do buyers actually want an inline answer-improver (Fusion's job) or a gateable decision artifact (the board's job)? Everything hinges on this and only inference is available.
- Does the cross-read-and-revise debate loop measurably outperform a cheaper compare-don't-merge or judge/synthesis-only panel — and would a published benchmark prove or disprove it?

## Next actions
- Rewrite positioning now (week 1, ~$0): a local deliberation workflow with a gateable, abstaining verdict that runs on your subscriptions at ~$0 marginal and can review your own code without it leaving the machine — naming the moat (debate + economics + privacy/local + CI-gateable verdict), not a 'Fusion-compatible model.'
- Ship a local one-shot escalation surface (e.g. `advisory-board ask` / MCP tool) as a thin wrapper over run_board.py: preflight, one quick board, optional --synthesize --strict-exit, returning verdict.json plus artifact paths — with strict timeouts and loud auth/latency warnings, and no metered/hosted path.
- Add additive informational schema/render fields (partial_coverage, unique_insights, blind_spots), strictly segregated and kept out of gate logic.
- Defer the published benchmark until the integration exists; when run, prefer gate precision/recall (does the abstaining gate catch decisions a solo model would ship that turn out wrong?) over deep-research accuracy on Fusion's turf, using logs from real one-shot escalations.
- Reject MCP/domain-tool pass-through for the gate+repo path by default; defer to local-only / read-only / capability-scoped advisory profiles.
- Defer sandboxed execution-grounded seats to a separate deep-dive, starting from command-evidence constraints rather than general bash access.

---
_Evidence status is a resolution check — it confirms the cited line exists or the quote is present in the captured material. It does not prove the inference drawn from it is sound (design §9)._

---
_An advisory board sharpens your judgment; it doesn't replace professional advice where your decision warrants it._
