# Memory formats

Both artifacts are plain markdown at the memory home the binding names. Both are written for the decider as much as for agents: plain English, no implementation detail, readable by a non-engineer in one pass.

## The terms file (glossary)

One file (e.g. `docs/terms.md`), updated in place:

```md
# Terms

**Order**:
A confirmed request to buy, from checkout to fulfillment.
_Avoid_: purchase, transaction

**Customer**:
A person or organization that places orders.
_Avoid_: client, buyer, account
```

Rules:

- **Be opinionated.** When several words exist for one concept, pick the canonical one and list the rest under `_Avoid_`.
- **Keep definitions tight.** One or two sentences; what the thing IS, not what the code does with it.
- **Project-specific concepts only.** General programming vocabulary (timeouts, retries, error types) stays out, however often the project uses it.
- **No implementation detail.** The glossary is a glossary — never a spec, a scratch pad, or a home for decisions (those are records).
- **Group under subheadings** when natural clusters emerge; a flat list is fine until they do.

## Decision records

One file per decision in the decisions directory (e.g. `docs/decisions/`), sequentially numbered `NNNN-slug.md` — scan for the highest number and increment. Parallel sessions can race that scan; a collision surfaces at merge and is resolved there as a checkable step: renumber the **younger** colliding record (it typically has no inbound references yet), rewrite every reference to or from the renumbered file — supersedes lines and forward markers included — and only then complete the merge. Lane close-outs being excluded as write moments keeps the window narrow:

```md
# 0007 — Postgres for the write model

- Date: 2026-08-07
- Links: #128, PR #131

We store the write model in Postgres rather than an event log: the team runs
Postgres already, and the audit needs are met by history tables at a fraction
of the operating cost.
```

One to three sentences is a complete record — the decision and the load-bearing reason. The value is that a future reader can tell new evidence from re-litigation; sections beyond that are bloat.

### Supersede markers

Records are superseded, never edited. A change of mind is a **new** record with a supersedes line:

```md
- Supersedes: [0007](./0007-postgres-for-write-model.md)
```

and the old record gains one line at the top — the only edit a record ever receives:

```md
> Superseded by [0019](./0019-event-sourced-write-model.md) — 2026-11-02.
```

## Attribution

Adapted from the [`CONTEXT-FORMAT.md`](https://github.com/mattpocock/skills/blob/main/skills/engineering/domain-modeling/CONTEXT-FORMAT.md) and [`ADR-FORMAT.md`](https://github.com/mattpocock/skills/blob/main/skills/engineering/domain-modeling/ADR-FORMAT.md) of Matt Pocock's `domain-modeling` (MIT): the glossary structure and its rules, the sequential numbering, and the a-paragraph-is-a-complete-record bar are his. The mandatory forward marker on never-edited records — where his format offers an optional, editable `Status` line — plus the links field and the plain-English-for-the-decider bar are this pack's.
