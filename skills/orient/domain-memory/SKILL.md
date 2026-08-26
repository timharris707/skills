---
name: domain-memory
description: "Keep per-repo institutional memory: a domain glossary plus lightweight decision records, written as side effects of work. Use when a grilling closes, a review rejection or declined finding is dispositioned, the decider corrects a session's wrong assumption, a session starts in a repo whose binding names a memory home, or the store passes its size bound."
---

# Domain memory

Per-repo institutional memory: what the repo's words mean, and why its settled decisions went the way they did. It is written as **side effects of work**, never as a documentation chore. [router](../router/SKILL.md) and [setup](../setup/SKILL.md) orient a session on the pack and the repo's bindings; this skill is the third orientation instrument beside them, and it orients the session on the domain.

This skill is the portable protocol: two artifacts in one store, the write and read moments that keep it alive, and evolution rules that keep it honest. Where the store lives, when consolidation is offered, and whether backfill runs are **binding slots** the team-workflow setup interview fills.

Read the team-workflow binding doc first; its domain-memory section names the memory home.

## 1. One store, two artifacts

- **The glossary**: one small, opinionated file of domain terms, each entry a canonical term, a tight definition, and the synonyms to avoid (the rules live in [references/formats.md](references/formats.md)). It updates **in place**: a term means one thing now, and the file says what.
- **Decision records**: one small file per settled decision, title, date, the decision, the **load-bearing reason**, and links to the ticket or PR that carried it. A record costs under a minute to write, in plain English a non-engineer decider reads without translation. The reason is the record's value: a future session needs to know *why*, so it can tell new evidence from re-litigation.

Formats for both live in [references/formats.md](references/formats.md). Files are created lazily: the glossary when the first term settles, the decisions directory when the first record lands; an empty store on day one is the correct starting state.

The store is repo files at the **memory home** the binding names: a decisions directory plus a terms file (e.g. `docs/decisions/` + `docs/terms.md`). The tracker holds work in flight; the repo carries the durable why: a decision's record outlives the ticket that produced it. And it is **one store**: in repos also bound to [codebase-review](../../investigate/codebase-review/SKILL.md), that skill's rejection-memory slot points at this memory home, so rejected candidates are decision records here, never a second store.

## 2. Write moments: side effects, never a chore

Memory is written at exactly three moments, each one a moment where a decision has just crystallised out loud:

1. **A grilling closes.** The [grilling](../../decide/grilling/SKILL.md) close-record mints memory: each settled decision becomes a decision record, and new or sharpened terms enter the glossary.
2. **A review disposition lands.** A [codebase-review](../../investigate/codebase-review/SKILL.md) rejection or an [adversarial-review](../../run/adversarial-review/SKILL.md) declined finding becomes a decision record with its load-bearing reason; the record is what stops the next review from re-raising settled ground.
3. **The decider corrects a session.** When the decider corrects a session's wrong assumption mid-flight, the session offers to record the correction: written down, the assumption is wrong exactly once. A [diagnose](../../run/diagnose/SKILL.md) root cause that overturns a standing assumption is the same correction class with reality as the corrector; the lane offers it as a fact record the same way, riding this moment rather than adding a fourth.

Lane close-outs are deliberately **not** a write moment: a lane executes a decision already recorded upstream, and recording every close-out buries the load-bearing records in noise.

These three are the **routine** writes. The store has exactly two **maintenance** writes beside them, an approved consolidation pass (§4) and accepted backfill drafts (§5), and each happens only under an explicit decider disposition: never skipped once the decider has given one, never performed without one.

## 3. Read moments

1. **Session start**: the orchestrator's startup checklist reads the glossary and skims recent decision records; any other session reaches the store through the binding doc's memory-home pointer.
2. **Grilling pre-round**: the griller reads the relevant records before asking, so a settled question is never re-asked; it reopens on new evidence, never on repetition.
3. **Lane briefs**: briefs point at the memory home, so a lane starts on the repo's terms and settled decisions instead of rediscovering them.
4. **Review layers**: finders and skeptics consult the decision records, so a review reads the why before contesting the what.

At every read moment, follow the supersession chain: only the latest unsuperseded record is **active**; a superseded decision or rejection is history, never authority.

## 4. Evolution: supersede, never edit

A decision record is **superseded, never edited**: a change of mind gets a new record carrying a "supersedes" link to the old one, and the old record gains a superseded marker pointing forward. Adding that Superseded-by marker is the one edit a record ever receives outside an approved consolidation pass ([references/formats.md](references/formats.md) states the two supersession steps). History stays readable: you can watch a decision change and see each reason standing at its own date. The glossary is the opposite case and updates in place: it says what a term means now, and its history is git's job.

Past the **size bound** the binding names, the skill offers a **consolidation pass**: a proposal to merge superseded chains, retire records whose subject no longer exists, and tighten the glossary, presented to the decider for disposition like any other proposal. The store shrinks only on the decider's yes, never on a session's tidying instinct.

## 5. Backfill: on request, by disposition

An existing repo starts empty and grows forward; that is the default, and it is correct. On the decider's request, a **one-time backfill lane** mines closed PRs, issues, and handoffs and **drafts** candidate records, presented card by card, [grilling](../../decide/grilling/SKILL.md)-style, for disposition. Nothing becomes memory without the decider's yes: an accepted draft becomes a record, a rejected one is dropped, and the lane never writes to the store directly.

## 6. Binding slots (the setup interview fills these per-repo)

- **Memory home**: where the store lives, a decisions directory plus a terms file the repo tracks.
- **Size bound**: the store size past which sessions offer the consolidation pass.
- **Backfill** (optional): whether the one-time backfill lane has been requested, and when.

## Done when (checkable)

- Every settled decision from the triggering write moment (grilling close, review disposition, or decider correction) is a record at the memory home carrying title, date, decision, the load-bearing reason, and links where a ticket or PR exists (a decider-correction record often has neither), or was declined by the decider; none is silently skipped.
- New or sharpened terms from the moment are in the glossary: canonical form, avoid-list, no implementation detail.
- No existing record was edited outside an approved consolidation pass, save adding a Superseded-by forward marker per formats.md's supersession steps: changes of mind are new records with supersedes links, and each superseded record carries its marker.
- The read moment in play actually read: session start, pre-round, lane brief, or review layer consulted the store, and nothing re-asked or re-raised a recorded decision without new evidence.
- A store past its size bound has the consolidation offer on the decider's table, and nothing was consolidated without disposition.
- Backfill drafts, where the lane ran, were each dispositioned card by card; nothing entered the store without a yes.

## Attribution

Adapted from Matt Pocock's [`domain-modeling`](https://github.com/mattpocock/skills/tree/main/skills/engineering/domain-modeling) (MIT). The mechanism is his: a repo glossary plus lightweight decision records (his `CONTEXT.md` and ADRs) as the two artifacts, written the moment a term or decision crystallises (a side effect of design work, not a documentation chore), files created lazily when the first entry exists, the glossary rules his [`CONTEXT-FORMAT.md`](https://github.com/mattpocock/skills/blob/main/skills/engineering/domain-modeling/CONTEXT-FORMAT.md) states (opinionated canonical terms with avoid-lists, tight definitions, project-specific concepts only) plus his SKILL.md's rule that the glossary stays devoid of implementation detail, and the record-can-be-a-paragraph bar of his [`ADR-FORMAT.md`](https://github.com/mattpocock/skills/blob/main/skills/engineering/domain-modeling/ADR-FORMAT.md): the value is recording *that* and *why*, not filling out sections.

What this repo changes: the write/read moment matrix wired into the pack (grilling close-records, review dispositions, and decider corrections in; session start, grilling pre-round, lane briefs, and review layers out), supersede-never-edit in place of editable ADR statuses, the consolidation pass offered past a size bound and dispositioned by the decider, the backfill-by-disposition lane, the unified store with codebase-review's rejection memory, the plain-English-for-the-decider bar, and the binding slots.
