# 0001 — Prune guard on lane workspaces

- Date: 2026-08-12
- Links: #184, PR #183 (CodeRabbit source thread)

The orchestrate skill's pruning step (§5 step 5) gains a one-sentence guard — check a
lane's workspace for uncommitted work and surface it before pruning — because pruning is destructive and a dirty
tree can hold real work; worth its cost against the 2,500-word bound.
