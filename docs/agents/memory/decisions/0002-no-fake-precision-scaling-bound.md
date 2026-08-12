# 0002 — No fake precision on the scaling bound

- Date: 2026-08-12
- Links: #184, PR #183 (CodeRabbit source thread)

Orchestrate §7's "before scaling past a lane or two" loses the number-shaped phrase
rather than gaining an exact bound: no measured threshold exists, so a number would
be fake precision.
