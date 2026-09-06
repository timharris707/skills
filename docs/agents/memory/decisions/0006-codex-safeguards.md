# 0006: Explicit Codex safeguards with preserved workflow choices

Status: accepted for implementation in issue #293, 2026-09-05.

The edition review agreed to restore actual trigger branches, require sourced
explicit decision-maker bindings, make review completion and correction review
checkable, and inspect checkpoints for secrets before and after saving.
Descriptions carry concrete invocation cases; offline assertions preserve those
branches but are not a model activation benchmark.

Keep proportional validation with required project and regression checks, deliver
review reports while adoption decisions remain tracked, and honor an explicitly
selected project voice. Same-task recovery remains the default. Distinguish
unverified provider candidates from successful authorized preflight and failed
checks. Document product capabilities separately from desktop observations and
workflow policy; validate live schemas and actual model routes.

The only intentional shared Claude behavior change in this correction is mixed
blocking: native ticket dependencies and a non-ticket `blocked` label coexist
when both are needed, and clear independently. General helper fixes remain owned
by the preceding upstream port (#291).

Acceptance evidence: [invocation cases](../../../../tests/codex/fixtures/invocation-cases.json),
[protocol regression checks](../../../../tests/codex/test_safeguards.py), and the
reviewed issue/PR verification records. No private machine policy is a public
installation input, and no comparative model-performance claim is made.
