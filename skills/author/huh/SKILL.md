---
name: huh
description: "Decode a message that didn't land: restate it in plain sentences, expand invented shorthand, split report from request, and flag claims stated without evidence. Use when the user signals your last message didn't land (\"huh?\", \"what do you mean\"), or pastes agent output from another session to translate."
---

# Huh

Decode one message that failed its reader. The output is a translation, nothing more: perform no new work, and add no facts the target does not carry.

## Target

Pasted text: decode that. Nothing pasted: decode your own most recent substantive message. Skip back past courtesies to the one carrying content, and use the conversation it sits in to resolve its references. A target from another session arrives without its context: resolve only what the text itself supports, and mark the rest unknown rather than guessing.

## The four moves

Work every move on the target.

1. **Restate.** Rewrite the whole message in complete plain sentences at the reader's altitude, defining every term of art in the sentence that first uses it.
2. **Expand the shorthand.** List every codename, label, abbreviation, or numbering scheme the message coined, each mapped to plain words, or marked unknown when the target does not say.
3. **Split report from request.** State separately what has already happened and what the reader is being asked to decide or do. When nothing is asked, say so outright; a reader hunting for a hidden question is half the confusion.
4. **Flag the unshown.** Name each claim presented as settled that the message backs with no evidence, number, or verification. This is bookkeeping, not accusation: "stated, not shown."

## Output shape

The restatement leads. After it, only the moves that found something, each a short labeled section: **Shorthand expanded**, **What's being asked of you**, **Stated but not shown**. The whole answer runs shorter than the target unless the target was too compressed to understand.

## Done when (checkable: verify each line before reporting complete)

- Every term of art in the restatement, whether coined by the target or inherited jargon, is defined in the sentence that first uses it.
- Every coined term is expanded or marked unknown; none is silently dropped.
- The reader can quote what is being asked of them, or the answer says nothing is.
- Every settled-sounding claim either carried its evidence in the target or is flagged.
- The answer performed no new work and added no fact the target does not carry.

## Attribution

The trigger is the same human moment as Matt Pocock's [wait-what](https://github.com/mattpocock/skills/tree/main/skills/productivity/wait-what) (MIT): the reader stops the agent and asks it to land the message this time. His skill is a two-line re-pitch prompt; the four moves, the target rules, and the output shape here were written independently for this catalog, from failure modes observed in its own sessions.

<!-- lineage: own -->
