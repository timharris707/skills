/**
 * The human copy layer — one entry per promoted skill, written for a reader
 * who does not code.
 *
 * SKILL.md descriptions are written for the agent that has to decide when to
 * fire them, and for years of this site's life they leaked straight onto the
 * human surfaces: catalog cards, page intros, link previews. This file is the
 * fix. Each entry is written from the reader's chair — the pain first, the
 * fix in plain words, and an honest limit where it earns trust — and never
 * borrows the agent's trigger vocabulary.
 *
 * `card` is the short form: the link-preview tagline and the catalog entry
 * line. `intro` is the longer form that opens the skill's own page. The agent
 * view is untouched by design: the Markdown twins behind the flip serve the
 * raw SKILL.md bytes, never anything from here.
 *
 * `human()` throws on a missing slug, so promoting a skill without writing
 * its human copy fails `next build` instead of quietly shipping agent text
 * back onto a human page.
 */

export type HumanCopy = {
  /** Link-preview tagline and catalog entry line. A few short sentences. */
  card: string;
  /** Opens the skill page: the pain, the fix in plain words, an honest limit. */
  intro: string;
};

export const HUMAN: Record<string, HumanCopy> = {
  // ── Orient ─────────────────────────────────────────────────────────────────
  router: {
    card:
      "You won't remember every skill in a pack this size, and you shouldn't have to. Ask your agent what fits the moment and it names the skill and says why. It points; it never runs anything on its own.",
    intro:
      "A pack this size has a findability problem: you won't remember every skill in it, and you shouldn't have to. router is the front door. Ask your agent what fits the situation and it names the right skill and says why. It's a map, not a manager — it points, and you decide whether to go.",
  },
  setup: {
    card:
      "One short interview teaches the pack how your project works: how you test, where the work is tracked, who has the final say. Answer once, and the other skills stop asking.",
    intro:
      "Every new tool asks you the same questions about your project, forever. setup asks them once. It's a short interview, run one time per project: how you test, where work is tracked, who has the final say. The answers are written down where every other skill can read them, so none of them has to ask again. It records how you already work; it never restructures anything.",
  },
  "domain-memory": {
    card:
      "What your project's words mean, and why old arguments were settled the way they were, written down as the work happens. A new session stops reopening decisions you already made.",
    intro:
      "Every project builds up a private language and a pile of settled arguments, and a fresh agent session knows none of it. So it asks again, or worse, quietly decides differently this time. domain-memory writes the language and the decisions down as a side effect of ordinary work: when a plan survives its interview, when a review finding is declined, when you correct a wrong assumption. It can only record decisions somebody actually stated out loud — it won't reconstruct why something was done last year.",
  },

  // ── Decide ─────────────────────────────────────────────────────────────────
  grilling: {
    card:
      "Your agent asks you every hard question before the work starts. Vague plans die in the interview instead of in the code.",
    intro:
      "You describe a feature, the agent agrees instantly, and hours later you're reviewing a polished version of something you never meant. The gaps you didn't fill, it filled with guesses. grilling flips the ritual: the agent interviews you, round after round of hard questions, until nothing important is still assumed and the answers are written down. Vague plans die in the interview instead of in the code. It works only as hard as your answers, so bring real attention.",
  },
  "advisory-board": {
    card:
      "One model's answer is one opinion. This puts the same question to Claude, Codex, Gemini, and Grok, lets them read each other, and hands you one verdict with the disagreement kept visible. The call is still yours.",
    intro:
      "A hard call — an architecture, a migration, a contract — usually gets decided by whichever model you happened to ask, in one pass, with nobody pushing back. advisory-board convenes Claude, Codex, Gemini, and Grok on the same question, has them answer independently, then read and challenge each other. You get one verdict with the disagreement kept visible and a list of what the board could not verify. It's slower than asking once, on purpose, and it's still models arguing with models: the final call stays yours.",
  },
  "decision-map": {
    card:
      "For work too foggy to plan in one sitting. The open questions go on a map, with what blocks what, and building waits until nothing the build rests on is still a guess.",
    intro:
      "Some work is too foggy to plan in one sitting: a new kind of feature, an integration nobody fully understands yet. Writing it up as a simple to-do list just hides the unknowns. decision-map charts the open questions instead, with what blocks what, and the map is worked question by question until nothing the build rests on is still a guess. It's for genuinely foggy work. If you could spec the thing in an afternoon, this is overhead.",
  },

  // ── Investigate ────────────────────────────────────────────────────────────
  ingest: {
    card:
      "Give it a call recording, a demo video, or a voice memo. You get back what was actually said, with timestamps and stills to prove it. It won't guess at words it can't hear.",
    intro:
      "An hour-long call recording is where decisions go to disappear. ingest turns a video, a recording, or a voice memo into evidence you can actually use: a transcript you can trust, stills with timestamps, and a recommendation for what to do with what was said. When the audio is bad, it marks what it couldn't hear rather than guessing.",
  },
  research: {
    card:
      "An agent goes and reads the actual sources: the vendor docs, the regulation, the upstream code. It comes back with findings you can check, each one pointing at where it was found.",
    intro:
      "Somebody has to actually read the vendor docs, the regulation, the upstream code, and it's tedious enough that mostly nobody does. research sends an agent to do the reading against the original sources and come back with findings you can check, each one pointing at where it was found. When the missing facts live in someone's head instead of a document, you get a list of questions for that person instead of a made-up answer.",
  },
  "codebase-review": {
    card:
      "Every so often, agents walk the whole codebase and report where it has gotten hard to work in. You decide what's worth fixing; nothing gets changed behind your back.",
    intro:
      "Agents merge work fast, and the codebase quietly accumulates the cost: duplication, drift, corners nobody owns. codebase-review is the periodic walk-through. Agents survey the whole codebase rather than one change and report where it has gotten hard to work in. It reports and files tickets; it fixes nothing behind your back, and it's no substitute for reviewing each change on its way in.",
  },
  prototype: {
    card:
      "Some design questions can't be settled by talking. This builds a quick throwaway version so you can click around and decide. The code is meant to be deleted, not shipped.",
    intro:
      "Some questions survive any amount of discussion: how should this screen feel, is this interaction annoying, which of these two layouts is right. prototype ends the debate by building the cheapest version you can actually click. The code is throwaway on purpose — it exists to answer the question, and it's deleted once the question is answered. Shipping it would be the mistake the skill exists to prevent.",
  },

  // ── Run ────────────────────────────────────────────────────────────────────
  diagnose: {
    card:
      "No bug fix ships until the agent can say what was actually broken, in one plain sentence, with evidence. A patch that just makes the symptom go away gets sent back.",
    intro:
      "The fastest way to keep a bug is to fix its symptom. An agent will happily patch until the error stops appearing and call it done. diagnose refuses that: no fix ships until the cause fits in one plain sentence, with evidence behind it. It's slower on the easy bugs, and worth it on every bug you'd otherwise meet twice.",
  },
  implement: {
    card:
      "The agent builds in thin slices that each work end to end, and proves each slice before starting the next. You get checkpoints you can see, not one long silence and a giant pile of code.",
    intro:
      "Left alone, an agent will build for an hour and hand you one giant batch of changes to untangle. implement is the building discipline: thin slices that each work end to end, a test written before the code it proves, a working checkpoint after every slice. Things discovered along the way get filed as new work instead of chased on the spot. You see progress you can check, not a long silence.",
  },
  "to-tickets": {
    card:
      "Turns a plan you've already settled into tracker tickets a stranger could pick up cold, in the right order. It won't paper over a plan that's still full of holes.",
    intro:
      "A plan that lives in a conversation dies with the conversation. to-tickets turns a settled plan into tracker tickets a stranger could pick up cold, with the order of work wired in so nothing starts before the thing it depends on. It needs the plan actually settled first. It won't paper over the holes, and it shouldn't.",
  },
  wizard: {
    card:
      "For the steps only you can do: passwords, vendor dashboards, DNS records. Your agent builds a walkthrough that takes you through click by click and checks that each step actually worked.",
    intro:
      "Some steps an agent simply cannot do for you: the password only you know, the vendor dashboard only you can log into, the DNS record on your registrar. wizard builds an interactive walkthrough for exactly those steps, taking you through click by click and checking that each step actually worked before moving on. If an agent could do the step itself, this is the wrong tool.",
  },
  orchestrate: {
    card:
      "One session becomes the manager. It hands work to parallel agents, checks what comes back, and owns fitting the pieces together. It needs a plan that's already decided; it won't decide for you.",
    intro:
      "Running several agents in parallel sounds like leverage, until you become the bottleneck between them. orchestrate turns one session into the coordinator: it routes work to parallel sessions, audits what comes back, and owns fitting the pieces together instead of building anything itself. It needs decided work sitting on a tracker to route. It won't untangle an undecided mess.",
  },
  "adversarial-review": {
    card:
      "Before anything ships, a team of agents tries to break it, and a skeptic tries to prove them wrong. Only problems that survive both reach you. I can't read the code, so the review has to be this honest.",
    intro:
      "You can't review what you can't read, and I can't read code. adversarial-review is how a change earns its way out anyway: a team of agents each tries to break it from a different angle, then a skeptic tries to prove every finding wrong. Only the problems that survive both passes reach you, so what you see is short and real. It blocks shipping on confirmed problems; it can't promise there are none left.",
  },
  "blast-radius": {
    card:
      "Before a change ships, this hunts for what it breaks somewhere else: past where grep stops, into library source, timing, and wire formats. Then it proves the one fact the change is safe because of by running real code, not by writing a risk list that merely sounds right.",
    intro:
      "Ask an agent whether a change is safe and you get a confident paragraph either way. blast-radius is the discipline a session runs on its own change before it merges: find the one fact the change is safe because of, look where a symbol search can't (library source at the pinned version, scheduling and teardown, the JSON on the wire, code three hops downstream), then prove that fact with a script that calls the real code and fails loud if it's wrong. Every safety claim gets a rung on an evidence ladder, and anything that stopped short of running code is labeled unproven instead of rounded up to settled.",
  },
  handoff: {
    card:
      "When a session ends, where the work stands goes into one small file. The next session reads it and picks up mid-stride. You stop re-explaining the project every morning.",
    intro:
      "Yesterday's session knew the plan, the constraints, and the half-finished thread, and this morning's session knows nothing. handoff ends a session by writing where the work stands into one small file, so the next session picks up mid-stride instead of interviewing you about the last one. It's a pointer, not a transcript: the deep history stays in the records the file points to.",
  },

  // ── Author ─────────────────────────────────────────────────────────────────
  "writing-for-agents": {
    card:
      "Instructions for agents fail quietly: read once, skimmed later, then ignored. This is my standard for writing instructions an agent will actually follow, and for cutting the ones it won't.",
    intro:
      "You write careful instructions for your agent, and three sessions later it's ignoring half of them. Usually the document is the problem: too long to load, too vague to fire at the right moment, too buried to find. writing-for-agents is the standard for the documents agents consume, and just as much for pruning them. It makes instructions predictable rather than beautiful; pages for people belong with its sibling, writing-for-humans.",
  },
  "writing-for-humans": {
    card:
      "Agents write pages that read like documentation for other agents. This is my standard for copy a person would keep reading, down to a last scrub for the phrases that give AI writing away.",
    intro:
      "Ask an agent for a landing page and you get something that reads like documentation wearing a costume: technically clear, and nothing a person wants to keep reading. writing-for-humans is the standard the pages on this site are held to. Open from the reader's chair, say plainly what a thing won't do, and scrub the phrases that give AI writing away. It can't supply the opinions — those still have to be yours.",
  },
  huh: {
    card:
      "When your agent's answer doesn't quite make sense, this reads it back in plain sentences and flags which parts are proven and which are just confident.",
    intro:
      "Agents produce messages that are confident, dense, and not quite parseable: invented shorthand, claims with nothing behind them, a request buried inside a report. huh reads the message back in plain sentences, expands the shorthand, separates what's being reported from what's being asked, and flags which claims come with evidence and which are just confident. It decodes; it can't verify the claims for you, only mark which ones arrived unproven.",
  },
  plainspoken: {
    card:
      "You can tell when an agent wrote something: the dashes, the padded phrases, the cheerful sign-off nobody asked for. This makes plain writing the default in every message your agent sends, chat replies and commit messages included. It fixes how things sound, and only that.",
    intro:
      "Ask an agent how the work went and you get a press release: everything is seamless, everything is a journey, and there's a dash in every sentence. plainspoken is the always-on voice rule for everything an agent writes, down to the chat replies and commit messages nobody thinks of as writing. Plain words, concrete claims, no dashes, no victory laps. When a passage still reads generated, it gets redrafted whole, because swapping one giveaway word for a synonym leaves the AI sentence standing. It governs how a message sounds, nothing more: whether the claim is true is a different discipline, and taste is still yours.",
  },
};

/**
 * The strict accessor every human surface goes through. Throwing here fails
 * `next build` for a promoted skill with no human copy — the regression this
 * file exists to prevent is agent text quietly returning to a human page.
 */
export function human(slug: string): HumanCopy {
  const copy = HUMAN[slug];
  if (!copy) {
    throw new Error(
      `human.ts: no human copy for "${slug}". Every promoted skill needs a card ` +
        "and an intro in src/lib/human.ts before it can ship to the site.",
    );
  }
  return copy;
}
