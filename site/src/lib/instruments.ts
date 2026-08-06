/**
 * Instruments — the tools the skills are run with.
 *
 * A surveyor's instruments are bought, not made. That is the line between this
 * page and /skills or /work: nothing here is a skill, and only one of these is
 * mine.
 *
 * Two rules, both inherited from the rest of the site:
 *
 *  1. Every card states where the instrument STOPS. A recommendations page
 *     that only ever says yes is worth less than one that says where each
 *     thing fails. The caveat is the reason to read the page, so it gets its
 *     own element rather than a clause buried at the end of a blurb.
 *  2. No star counts and no version numbers. They drift weekly and a reader
 *     who checks one and finds it stale discounts everything else. Maturity is
 *     stated qualitatively; the page carries a checked date instead, the way
 *     a Survey does.
 */

export type Instrument = {
  name: string;
  /** Licence and maturity, as the status chip. */
  status: string;
  blurb: string;
  /** Where it stops. Never omitted — if there is no caveat, it does not belong. */
  stopsAt: string;
  url?: string;
  repo?: string;
  /** Mine, so the page never pretends to be neutral about it. */
  mine?: boolean;
};

export type Bench = {
  id: string;
  name: string;
  blurb: string;
  instruments: Instrument[];
};

/** Re-verified when the page is reviewed, like a Survey's claims. */
export const CHECKED = "2026-08-05";

export const BENCHES: Bench[] = [
  {
    id: "ground-truth",
    name: "Ground truth",
    blurb:
      "An agent that greps and finds nothing concludes nothing is there. These answer from the graph instead.",
    instruments: [
      {
        name: "Fallow",
        status: "MIT · one maintainer, shipping fast",
        blurb:
          "One Rust binary that reads a TypeScript or JavaScript repository as a single dependency graph and reports what the graph shows: unused files, exports and dependencies, circular imports, duplication, complexity, architecture-boundary violations. It is here for one job — deletion safety. An agent asked whether a symbol is safe to remove will grep, find nothing, and delete something reached through a re-export chain. Its exit codes distinguish “found problems” from “broke”, so an agent loop can branch on the difference instead of swallowing it, and its audit mode fails only on findings the current change introduced — which is the property that lets you switch it on in a repository that already has a backlog.",
        stopsAt:
          "TypeScript and JavaScript only, with no sign of that widening. One maintainer at roughly a release a day: the risk is not abandonment, it is a flag or an output shape moving underneath a workflow you built on it, so pin the exact version rather than a range. “Codebase intelligence” oversells it — this is four mature analysis categories consolidated behind one typed contract, not new analytical power.",
        url: "https://fallow.tools",
        repo: "https://github.com/fallow-rs/fallow",
      },
      {
        name: "CodeGraph",
        status: "MIT · one maintainer",
        blurb:
          "A local code knowledge graph — functions, classes and methods as nodes, calls and imports and inheritance as edges — held in SQLite and offered to agents through a single MCP tool, a CLI and a library. The indexing is the ordinary half; several projects do that. What earns it a card is that the maintainer measured whether agents actually used the index, found that by default they largely did not, and shipped countermeasures: instructions naming the anti-patterns, a block written into the agent instructions file because MCP guidance never reaches subagents, auto-allow permissions so an approval prompt is not what kills adoption, and one tool rather than eight because a menu produced mis-picks. That is the behavioural half of the problem being taken seriously, and it is the half the research says actually binds.",
        stopsAt:
          "Every performance number is the project's own, and it has already had to withdraw earlier figures after finding its control arm had reached the graph through the shell. To its credit it publishes the metric it loses: answers leave substantially more retrieval context resident at the end of a long session. Small repositories and narrow questions do not pay for the overhead.",
        repo: "https://github.com/colbymchenry/codegraph",
      },
    ],
  },
  {
    id: "second-reader",
    name: "Second reader",
    blurb:
      "An agent reviewing its own diff shares its own blind spots. This is a different system reading the same change.",
    instruments: [
      {
        name: "CodeRabbit",
        status: "proprietary · free for open source",
        blurb:
          "A hosted reviewer that clones the repository into a sandbox, runs fifty-odd conventional linters and scanners against it using your existing configuration, and folds their output into a review posted as line-level comments. The reason to run it rather than asking a model to read the diff is plumbing rather than model quality: whole-repository context instead of a diff in a prompt, real tool output instead of a guess at what the tools would have said, and review memory you can edit. For directing agents the surface that matters is its structured JSON output, which lets a generate-review-iterate loop run with the reviewer as a different system from the generator.",
        stopsAt:
          "It is tuned to miss less and say more, and the price of that is precision. An independent month-long audit of 290 comments across 28 pull requests found 15% useless and 13% resting on wrong assumptions, alongside 35% that genuinely improved the change. Budget the tuning, use path filters, and do not make it the merge gate. And its own FAQ is explicit that your code is sent to OpenAI and Anthropic — full retention opt-out exists only on self-hosted enterprise.",
        url: "https://www.coderabbit.ai",
      },
    ],
  },
  {
    id: "capacity",
    name: "Capacity",
    blurb:
      "Neither of these improves any output. They decide which account the work runs on, and tell you when it is about to run out.",
    instruments: [
      {
        name: "CLIProxyAPI",
        status: "MIT · very active",
        blurb:
          "A local Go proxy that puts an OpenAI-, Anthropic- and Gemini-shaped API in front of several CLI-subscription accounts, so any client reaches the whole pool through one localhost port. Three selection strategies — round-robin, weighted round-robin with a per-account integer weight, and fill-first, which its own source documents as a way to stagger rolling-window caps. It exists because several accounts otherwise means several tools, and because one window running out mid-task while another account sits idle is an avoidable way to lose a session.",
        stopsAt:
          "Whether pooling paid subscription accounts behind one endpoint is permitted is governed by each provider's own subscriber terms. The project publishes no position on this — its repository carries no terms, disclaimer or acceptable-use text at all — and I have not read those terms either. Read yours before running it. Two other things worth knowing: its README is monetised with affiliate links to API-relay and account-resale vendors, which is context for how it describes itself; and built-in usage statistics were removed, so it routes but does not tell you what it spent.",
        repo: "https://github.com/router-for-me/CLIProxyAPI",
      },
      {
        name: "ModelDeck",
        status: "mine · free, macOS",
        mine: true,
        blurb:
          "Mine, and the reason the proxy above is on this page rather than in a drawer. ModelDeck shows how much Claude Code and Codex capacity is left across every account you run; where a proxy auth directory is configured it also reads each account's routing weight out of those files and puts it on the card beside the remaining capacity, so “which way is the weighting leaning” and “which account is nearly out” become one glance instead of two tools. It reads four non-secret fields and nothing else. The OAuth tokens sitting in the same files are never touched, there is no write path, and the directory is never auto-discovered.",
        stopsAt:
          "Read-only by design, and macOS only. It reports; it sets no weights and will never rotate an account on your behalf. Every failure mode reads as plain absence, so a machine without the proxy simply shows nothing.",
        url: "https://modeldeck.ai",
        repo: "https://github.com/timharris707/modeldeck",
      },
    ],
  },
];

/**
 * The closing note: the loop those last two cards make when the weighting sits
 * between them. Described rather than shipped — it is machine-local
 * infrastructure welded to one setup, not a portable skill, and putting it in
 * the catalog would be a category error.
 */
export const CLOSING_THE_LOOP = {
  title: "Closing the loop",
  body: [
    "Those last two cards read; nothing in them decides. The piece that decides is the weighting — a job that runs every five minutes, asks ModelDeck what each account has left, works out a weight for each one, and writes those weights into the proxy, which routes on them. ModelDeck observes and the weighting decides; neither ever touches a provider credential.",
    "The part worth stealing is the policy rather than the plumbing. Weighting on raw remaining capacity is the obvious approach and it is wrong, because quota left unused when the window resets is simply wasted. So the weight is pace-based: divide what remains by how much of the cycle remains, and an account with plenty left and an imminent reset gets drained first while an account burning ahead of schedule gets conserved. A floor keeps a nearly empty account out of the pool entirely, because a drained account returns errors rather than results.",
    "It is not in this catalog and it is not going to be. The skills here are a portable discipline that binds to any repository; this is one machine's infrastructure, and it belongs beside ModelDeck rather than pretending to be a skill.",
  ],
};
