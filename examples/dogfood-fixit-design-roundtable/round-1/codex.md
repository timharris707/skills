**Verdict**
Caution, high confidence. I would move to ship if Q1/Q3/Q8 are tightened: stable edit identity, diff-hunk anchoring, no metadata header inside the clean revised draft, and explicit endorsement semantics.

**Q Rulings**
Q1: CAUTION. Do not key only by exact title. Titles are usable for `amend` because a human is in the loop, but `changes.json` is machine provenance. Use conductor-assigned optional finding ids now, or at minimum `{list, index, title}` with duplicate-title detection.

Q2: SHIP with guardrails. File plus `verdict.json.changes` pointer is right, but write it atomically with the same lost-update discipline as `amend`, and include a non-circular verdict pin in `changes.json`, such as `verdict_sha256_without_changes`.

Q3: CAUTION. Original-only line ranges are too weak. They cannot cleanly represent insertions, deletions, or multi-hunk edits. Use diff-hunk locators with original and revised spans plus hunk hashes. Yes, every blocker must be resolved or unresolved; concerns/caveats can stay best effort.

Q4: SHIP. Heuristic plus `--source-type prose|code` override is the right trade-off. Unknown extensions, stdin, and URL-like sources should refuse until explicit. Persist the resolved value in the recipe.

Q5: SHIP the one-spawn design, but not static fences. Use per-run high-entropy output markers not present in source/verdict, or a robust JSON envelope. Keep rejected artifacts and strict-exit behavior aligned with synthesis.

Q6: SHIP ON by default. But define semantics: “board-endorsed” only when every non-revision usable seat endorses. Any `OBJECT` or `ABSTAIN` makes the artifact “reviewed with objections/abstentions,” not endorsed. `--no-endorse` must label the artifact unendorsed.

Q7: SHIP. Conflicts should produce partial work plus `unresolved`, no content-based exit-code change. If all blockers are unresolved, the draft may still exist, but every render/run-card/header sidecar must make that impossible to miss.

Q8: CAUTION. Do not put a provenance header inside `revised-draft.md`; that pollutes the clean artifact the human applies. Put metadata in `changes.json`, HTML, or a sidecar. Also generate a unified diff for prose, not only HTML redline. Require a validated `verdict.json`, but do not require it to be synthesized; support human-authored verdicts via a post-hoc command or documented flow.

**Strongest Objections**
The clean revised draft must be clean. A header inside prose changes the user’s document.

Title-only identity will break on duplicate titles, hand edits, or later consumers. The current validator does not enforce finding-title uniqueness.

The proposed `locator: lines from/to` is not enough for insertions, deletions, replacements spanning multiple hunks, or conductor validation of model-provided mappings.

Endorsement needs an explicit aggregate state; raw rows alone let marketing outrun provenance.

A same-run `--synthesize` requirement would exclude the project’s existing hand-authored-verdict workflow.

**Recommended Execution Sequence**
1. Record D9+ decisions before coding, especially identity, `changes` pointer, endorsement semantics, and clean-artifact rule.
2. Add schema/validator tests first: optional ids or `{list,index,title}`, `changes` pointer, `changes.json`, duplicate-title behavior, blocker completeness.
3. Add `--source-type` config/recipe/run-card plumbing and resolve-time refusal rules.
4. Generalize synthesizer spawn substrate into reusable post-round model-spawn helpers.
5. Implement revision step: validated verdict in, robust section parsing, clean revised artifact, generated diff/patch, validated `changes.json`, rejected artifacts on failure.
6. Add local renderers: prose redline HTML, code patch fenced view, no XSS/template leakage.
7. Add endorsement pass and update `changes.json`/pointer only after successful validation.
8. Finish with fixture-heavy tests: duplicate titles, insert/delete-only edits, no trailing newline, path spaces, large sources, all-unresolved, objected endorsement.

**Invariants And Guardrails**
The source file is never written. Default/no-flag artifacts remain byte-identical. Models never mint provenance, ids, shas, statuses, or endorsement aggregates. `revised-draft.*` contains only the revised source content. Every blocker is accounted for. `changes.json` pins source, revised artifact, verdict basis, revision seat, source type, and endorsements. All HTML redline content is escaped before `<ins>/<del>` insertion. Patch paths are deterministic and safe.

**Risks / Missing Evidence**
No size policy is stated for full-source rewrite responses. No patch-path policy is stated for files outside repo root, stdin, spaces, or absolute paths. No proof that static output fences survive adversarial source content. No UX language defines “endorsed” vs “objected” vs “unendorsed.” No post-hoc flow is specified for validated human-authored verdicts.

**Concrete Evidence**
`--output` currently only has three enum choices in [scripts/_conductor/cli.py](skills/advisory-board/scripts/_conductor/cli.py:705), and `config.output` is printed/persisted in [artifacts.py](skills/advisory-board/scripts/_conductor/artifacts.py:103) and [recipe.py](skills/advisory-board/scripts/_conductor/recipe.py:240).

`SourceSpec.kind` is transport only in [config.py](skills/advisory-board/scripts/_conductor/config.py:51). `changes` is currently refused in [board_verdict.py](skills/advisory-board/scripts/board_verdict.py:142). `amend --on` uses title lists in [board_verdict.py](skills/advisory-board/scripts/board_verdict.py:525).

The renderer is token/block substitution in [_render_engine.py](skills/advisory-board/scripts/_render_engine.py:1); current diff machinery is unified diff in [revise.py](skills/advisory-board/scripts/_conductor/revise.py:249) and title similarity in [delta.py](skills/advisory-board/scripts/_conductor/delta.py:15).

**Ask Other Seats**
Challenge whether `verdict.json` should be reopened at all, whether default endorsement cost is acceptable, whether optional ids are worth the schema churn, and whether the “board-endorsed” UX can stay honest when seats object.

VERDICT: caution
