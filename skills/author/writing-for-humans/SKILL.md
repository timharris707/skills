---
name: writing-for-humans
description: Write copy a human reads — a landing page, a README's front half, a launch post, a profile page. Use when drafting or revising public-facing prose, when a page reads like agent documentation, or when a finished draft needs its last-mile scrub for AI tells.
---

# Writing for Humans

The sibling skill [writing-for-agents](../writing-for-agents/SKILL.md) makes documents predictable enough that an agent runs the same process every time. This skill makes pages worth a stranger's next minute: the reader is free to leave at any sentence, and the page earns each one. The compression that serves an agent reads cold to a human; when the document is a SKILL.md, an AGENTS.md, or a reference an agent consumes, use the sibling instead.

Work the sections in order for a full draft. Jump straight to [the scrub](references/last-mile-scrub.md) when the content already stands and only the tells remain.

## Guide structure over catalog structure

A catalog lists what exists. A guide walks the reader somewhere. Human-facing pages take the guide shape, in this order:

1. **Identity and hook first.** One or two sentences before any list: what this is, for whom, and the opinion that animates it.
2. **The quickest possible start.** The smallest real action the reader can take right now, finishable in minutes.
3. **Problems framed from the reader's seat.** Each runs problem → fix → link: the pain as the reader feels it, then the fix, then where to go.
4. **Explicit ordering.** "Start here. Do this first." The reader never infers the sequence.
5. **Full reference last.** The complete listing sits at the bottom, where the convinced reader looks it up, not at the top where it greets the undecided one.

The test at every scroll depth: can the reader say what to do next? A section that leaves them informed but directionless goes lower or gets a pointer forward.

## Warmth moves

Warmth is specific moves, each observable in the text:

- **First person with real opinions.** "I built this because X annoyed me" over "This tool addresses X." An opinion is a claim the writer could lose an argument about.
- **Admit limits plainly.** "It won't untangle the mud for you" builds more trust than any capability claim. Every piece carries at least one honest limit.
- **Permission-giving imperatives.** "Hack around with them. Make them your own." The reader is invited to act, not licensed to observe.
- **Empathy before feature talk.** Open from the reader's chair, then introduce what you built. A feature named before its pain is a spec line, not a sentence.

## Failure modes

Check a draft against each by name:

- **Agent-register bleed** — human copy in the compressed declarative style of agent docs. The tell is a term of art standing where a reader's word should be; translate it or teach it in the sentence where it first appears.
- **Process bleed** — the piece narrates the hidden work behind it: chat history shipping as copy. Write from the facts, ordered by the reader's questions, never by the build timeline.
- **Clean nothing** — tidy, de-AI'd, and empty. A scrub is not a voice. The test: does the piece contain an opinion, an admitted limit, or a choice a competitor's page wouldn't make?

## Standing voice rules

Warmth never buys these back:

- **Checkable claims only.** Every claim hands the reader a way to verify it: a link, a sourced number, or a behavior they can try. A claim that offers none is absent.
- **No stale numbers.** A count or date that will rot either lives where the release process updates it, or is written so it cannot rot ("the catalog table below is the current list").
- **Facts sacred.** Never invent a user, an anecdote, or a metric to sound human. Where a fact is missing, leave a visible placeholder and go get the fact.
- **Names only in praise.** A person or company is named in your copy only when the mention flatters them.
- **Dashes on a budget.** The em dash is one of the most recognized AI tells, and the clause-spliced rhythm it builds is the reason. A handful per page at most, each an earned interruption. Fix an overage by restructuring: split the sentence, subordinate with a comma, or cut the aside. Never swap a dash for another mark in place; the swap keeps the AI rhythm and only changes its costume.
- **Positioning is canon, reused verbatim.** The identity hook "I don't write code. I direct agents." and the wedge "I don't write code. I've shipped four products in five months." are standing first-person lines, never paraphrased (the wedge's numbers fall under no-stale-numbers: verify before use). The positioning stands on two legs, and copy carries both: interesting because the writer is not a coder, believable because the work is shown. The skills catalog is always positioned as the method that let a non-coder ship four products, never as generic portable skills. The canon lives in personal-marketing PLAN.md §1 and §7; when this skill and that doc disagree, the doc wins and this rule gets amended.

## Last-mile scrub

After structure and voice are settled (never before, or you produce clean nothing), run [references/last-mile-scrub.md](references/last-mile-scrub.md). Start with the guardrails: hunt clusters rather than isolated tells, and let a voice sample outrank any conflicting tell rule (the standing voice rules above are never outranked). Rewrite whole sentences rather than swapping words.

## It's working if

Qualities of the finished page, judged by reading it cold:

- A reader who has never seen the project can say what to install (or read, or click) first and what their first session looks like.
- The piece carries at least one first-person opinion and one plainly admitted limit: something a competitor's page would not say.
- The page is scrubbed but not silenced: free of AI tells and still audibly voiced. A page that is only cleaner is clean nothing; put voice back before shipping.
- What the reader gets and does next fills the page; how it got made appears nowhere.

## Done when (checkable: verify each line before reporting complete)

- Hook first, quickest start second, reference last; every section leaves a visible next action.
- No insider term appears before the sentence that teaches it: the page teaches its vocabulary or drops it.
- Every claim is checkable or absent, every number has a live source or cannot rot, and nothing was invented to sound human.
- The dash budget was spent deliberately, and no over-budget dash was fixed by an in-place swap.
- The scrub ran last, whole clusters were rewritten, and the voice sample (when one exists) won every conflict with the tell rules.
- Every line of "It's working if" was checked against the final text, not assumed.

## Attribution

The guide structure is modeled on the README of Matt Pocock's [skills](https://github.com/mattpocock/skills) (MIT): hook, thirty-second start, problem → fix framing, and reference last are the shape his README demonstrates; the quoted phrases in Warmth moves ("it won't untangle the mud for you", "Hack around with them. Make them your own.") are his, and the *It's working if* section follows the outcome-test shape of his skill docs pages. *Process bleed* is [forint573/human-copywrite](https://github.com/forint573/human-copywrite)'s term (Apache-2.0). The scrub's guardrails (clusters over isolated tells, voice sample outranks the tell rules, no fabrication) follow [blader/humanizer](https://github.com/blader/humanizer) (MIT), whose 33-pattern catalog builds on Wikipedia's "Signs of AI writing"; the dash budget is a softer cousin of that skill's outright em-and-en-dash ban. What this catalog adds: the register split against its sibling writing-for-agents, the *agent-register bleed* and *clean nothing* failure modes, the standing voice rules, and the two checkable exit sections.
