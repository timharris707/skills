# 0001 — Prune guard in, fake-precision phrase out

- Date: 2026-08-12
- Links: #184, PR #183 (CodeRabbit source threads)

Two decider calls on the orchestrate skill's CodeRabbit follow-ups. The pruning step
(§5 step 5) gains a one-sentence guard — check a lane's workspace for uncommitted work
before pruning it — because pruning is destructive and a dirty tree can hold real work;
worth its cost against the 2,500-word bound. And §7's "before scaling past a lane or
two" loses the number-shaped phrase rather than gaining an exact bound: no measured
threshold exists, so a number would be fake precision.
