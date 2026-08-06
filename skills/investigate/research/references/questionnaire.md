# The questionnaire terminal move

When a research lane hits facts only an external human holds, it ends by emitting a questionnaire file — `docs/research/questionnaire-<topic>.md` (or a git-ignored location when the content is PII-adjacent) — linked from the driving ticket.

**Craft rule: grill the SEND, not the subject.** Before drafting a single question, settle with the decider who the questionnaire goes to and what is needed back. A perfect question list aimed at the wrong recipient is wasted; the recipient and the decision the answers feed determine everything about the questions.

## The file's shape

1. **Header**: purpose + how the answers will be used.
2. **One-paragraph context** for the recipient — enough to answer well, no more.
3. **Sections ordered most-important-first** — async means assume one pass; if the recipient answers only the first section, that section must be the one that mattered.
4. **One idea per question**, with an answer stub beneath each.
5. **"Partial answers and 'I don't know' are useful"** stated up front — an honest gap beats a guessed answer.
6. **A closing catch-all**: "anything we didn't ask about that we should have?"

## After emitting

The research lane is done — sending the questionnaire and chasing answers is the decider's (or the ticket owner's) real-world move, recorded back on the ticket when the answers land.
