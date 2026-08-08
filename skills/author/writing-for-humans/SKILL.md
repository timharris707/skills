---
name: writing-for-humans
description: Write copy a human reads — a landing page, a README's front half, a launch post, a profile page. Use when drafting or revising public-facing prose, when a page reads like agent documentation, or when a finished draft needs its last-mile scrub for AI tells.
---

# Writing for Humans

A human reads for a different reason than an agent. The sibling skill [writing-for-agents](../writing-for-agents/SKILL.md) makes documents predictable — the same process every run. This skill makes pages worth a stranger's next minute: the reader is free to leave at any sentence, and the page earns each one. The registers are opposites, and the compression that serves an agent reads cold to a human — so when the document you are writing is a SKILL.md, an AGENTS.md, or a reference an agent consumes, use the sibling instead.

Work the sections in order for a full draft; jump straight to [the scrub](references/last-mile-scrub.md) when the content already stands and only the tells remain.

## Guide structure over catalog structure

A catalog lists what exists. A guide walks the reader somewhere. Human-facing pages take the guide shape (modeled on the [mattpocock/skills](https://github.com/mattpocock/skills) README), in this order:

1. **Identity and hook first.** One or two sentences saying what this is, for whom, and the opinion that animates it — before any list.
2. **The quickest possible start.** The smallest real action the reader can take right now, stated as steps they can finish in minutes.
3. **Problems framed from the reader's seat.** Each one runs problem → fix → link: name the pain as the reader feels it, then the fix, then where to go. The reader's frustration comes before your feature every time.
4. **Explicit ordering.** Say outright what to do first, second, and when each later piece becomes relevant. "Start here. Do this first." The reader never infers the sequence.
5. **Full reference last.** The complete listing exists — at the bottom, where the convinced reader looks it up, not at the top where it greets the undecided one.

The structural test at every scroll depth: can the reader say what to do next? A section that leaves them informed but directionless goes lower or gets a pointer forward.

## Warmth moves

Warmth is specific moves, each observable in the text:

- **First person with real opinions.** "I built this because X annoyed me" over "This tool addresses X." An opinion is a claim the writer could lose an argument about.
- **Admit limits plainly.** Confessing what a thing won't do is the warmest move available — "it is a survey, not a rescue; it won't untangle the mud for you" builds more trust than any capability claim. Every piece carries at least one honest limit.
- **Permission-giving imperatives.** "Hack around with them. Make them your own." The reader is invited to act, not licensed to observe.
- **Empathy before feature talk.** Open from the reader's chair — the situation they're in, the thing that isn't working — and only then introduce what you built. A feature named before its pain is a spec line, not a sentence.

## Failure modes

Check a draft against each by name:

- **Agent-register bleed** — human copy written in the compressed declarative style of agent docs: single-verb headers, definition-dense paragraphs, insider vocabulary presented as self-evident. The tell is a term of art standing where a reader's word should be. Translate the term or teach it in the sentence where it first appears.
- **Process bleed** — the piece narrates the hidden work behind it instead of speaking to the reader about what they get and what to do next. (The term is [forint573's](https://github.com/forint573/human-copywrite): chat history shipping as copy.) The fix is to write from the facts, ordered by the reader's questions — never by the build timeline.
- **Clean nothing** — tidy, de-AI'd, and empty: every tell scrubbed, no voice left. A scrub is not a voice. The test: does the piece contain an opinion, an admitted limit, or a choice a competitor's page wouldn't make? Zero of the three means you polished a vacancy.

## Standing voice rules

These carry over from the agent-facing register unchanged — warmth never buys them back:

- **Checkable claims only.** Every claim is verifiable by the reader — a link, a number with a source, a demonstrable behavior — or it is absent.
- **No stale numbers.** A count or date that will rot ("twelve integrations", "as of March") either lives where the release process updates it, or is written so it cannot rot ("the catalog table below is the current list").
- **Facts sacred.** Never invent a detail — a user, an anecdote, a metric — to sound human. A fabricated warm detail is worse than a cold true one. Where a fact is missing, leave a visible placeholder and go get the fact.
- **Anonymize criticism; names only in praise.** A person or company is named in your copy only when the mention flatters them.
- **Positioning is a standing fact, reused verbatim — and it is first-person.** The canonical lines are the identity hook "I don't write code. I direct agents." and the wedge "I don't write code. I've shipped four products in five months." (verify the shipped count is current before using — this rule's own no-stale-numbers bar applies to it). The third-person descriptor — a non-coder CEO shipping software via agents, lending as background credibility kept in the background — is rationale prose, not the line copy reaches for. The positioning has two legs and copy carries both: interesting because not a coder, believable because the work is shown ("And I check what the frontier actually claims"); leg one without leg two reads as a stunt. The skills catalog itself is always positioned as the method that let a non-coder ship four products, never as generic portable skills for agents. Source of canon: the marketing plan's positioning and voice sections (personal-marketing PLAN.md §1, §7); when this skill and that doc disagree, the doc wins and this rule gets amended.

## Last-mile scrub

After structure and voice are settled — never before, or you produce clean nothing — run the AI-tell pass in [references/last-mile-scrub.md](references/last-mile-scrub.md): guardrails first (clusters, not isolated tells; a voice sample outranks every rule), then the tell clusters, rewriting whole sentences rather than swapping words.

## Done when (checkable — verify each line before reporting complete)

- A reader who has never seen the project can say what to install (or read, or click) first and what their first session looks like — test by reading only the page.
- Hook first, quickest start second, reference last; every section leaves a visible next action.
- No insider term appears before the sentence that explains it — the page teaches its vocabulary or drops it.
- Every claim is checkable or absent, every number has a live source or cannot rot, and nothing was invented to sound human.
- The piece carries at least one first-person opinion and at least one plainly admitted limit.
- The piece describes what the reader gets and does next — nowhere how the piece itself got made.
- The last-mile scrub ran last, whole clusters were rewritten, and the voice sample (when one exists) won every conflict with the rules.

## Attribution

The guide structure is modeled on the README of Matt Pocock's [skills](https://github.com/mattpocock/skills) (MIT) — hook, thirty-second start, problem → fix framing, and reference last are the shape his README demonstrates, and the quoted phrases in Warmth moves ("it won't untangle the mud for you", "Hack around with them. Make them your own.") are his. *Process bleed* is [forint573/human-copywrite](https://github.com/forint573/human-copywrite)'s term (Apache-2.0). The scrub's guardrails — clusters over isolated tells, voice sample outranks the rules, no fabrication — follow [blader/humanizer](https://github.com/blader/humanizer) (MIT), whose 33-pattern catalog builds on Wikipedia's "Signs of AI writing". What this catalog adds: the register split against its sibling writing-for-agents, the *agent-register bleed* and *clean nothing* failure modes, the standing voice rules, and the checkable done-when list.
