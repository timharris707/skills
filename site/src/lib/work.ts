/**
 * The work behind the catalog.
 *
 * Unlike the skills, this is hand-written — there is no manifest to generate it
 * from. Two rules hold it honest:
 *
 *  1. Nothing here states a number a reader could check and find stale: no
 *     version numbers, no star counts, no download counts, no ship dates.
 *  2. Private builds name a capability and a standard, never a mechanism. How a
 *     guarantee is enforced is a map for anyone probing it; that it holds is
 *     the only part a reader needs.
 */

export type Build = {
  name: string;
  /** What it is and who it is for, in the site's voice. */
  blurb: string;
  /** The status chip. Coarse on purpose — "in build" is the finest resolution
   *  private work gets. */
  status: string;
  site?: string;
  repo?: string;
};

export type Waters = {
  id: string;
  /** Lettered like a chart region, in italic serif. */
  name: string;
  blurb: string;
  /** Shown under the blurb where the convention needs explaining. */
  note?: string;
  builds: Build[];
};

export const WORK: Waters[] = [
  {
    id: "charted",
    name: "Charted",
    blurb: "Public repositories, public sites. Install them and check the work.",
    builds: [
      {
        name: "ModelDeck",
        blurb:
          "Shows how much Claude Code and Codex capacity is left across every account you run — before a session dies mid-task, rather than after. Local-first by design: no cloud, no telemetry, and it will never rotate an account on your behalf. It warns; you decide.",
        status: "shipping · macOS",
        site: "https://modeldeck.ai",
        repo: "https://github.com/timharris707/modeldeck",
      },
      {
        name: "Panely",
        blurb:
          "Frontier models take separate seats on an advisory board, read each other's reviews across rounds, and hand back one plain-language verdict — with the dissent preserved and an explicit list of what the board could not verify. One idea in three forms: a local-first web app, a native macOS build, and the advisory-board skill in this catalog.",
        status: "shipping",
        site: "https://panely.ai",
        repo: "https://github.com/timharris707/panely",
      },
      {
        name: "HiveRunner",
        blurb:
          "Turns one goal into a planned sprint and runs it across whichever coding agents you already have — Codex, Claude Code, Gemini, any CLI — as interchangeable workers on a single board. Nothing an agent produces counts as done until a human accepts it.",
        status: "pre-1.0 · open source",
        site: "https://hiverunner.ai",
        repo: "https://github.com/timharris707/hiverunner",
      },
      {
        name: "Click AI",
        blurb:
          "This site. Self-contained playbooks any agent can read, shipped identically to Claude Code and Codex — CI fails the build if the two would ever ship a different set. The catalog is generated from the skills themselves, so the documentation cannot drift from what installs.",
        status: "shipping · MIT",
        site: "/skills",
        repo: "https://github.com/timharris707/skills",
      },
    ],
  },
  {
    id: "unsurveyed",
    name: "Unsurveyed",
    blurb: "Private builds, inside my own company. Shape shown, soundings withheld.",
    note: "On a chart, blank water is not empty water — it is water nobody has surveyed. Same idea here. What these do is fair to state. What they are worth, who runs on them, and when they land is not.",
    builds: [
      {
        name: "LoanMeld",
        blurb:
          "A multi-tenant loan management system for consumer lenders, built so the audit trail falls out of ordinary work instead of being assembled afterwards. Every tenant isolated at the database, money movement that has to balance, borrower data masked by default. The largest build on this page and the one with the least room for error.",
        status: "in build · private",
      },
      {
        name: "Bullpen",
        blurb:
          "A self-hosted team chat where engineers and their coding agents share the same rooms, so an agent's work is visible to the whole team instead of trapped in one person's terminal. The record is append-only: nobody can rewrite what happened after the fact, including whoever runs the server.",
        status: "in build · private",
      },
    ],
  },
];

export const BUILD_COUNT = WORK.reduce((n, w) => n + w.builds.length, 0);
export const PUBLIC_COUNT = WORK.find((w) => w.id === "charted")!.builds.length;
export const PRIVATE_COUNT = WORK.find((w) => w.id === "unsurveyed")!.builds.length;

/**
 * The short form, for the homepage. Kept to about fifty words on the model of
 * the sites this one learned from: the reader meets the argument and the
 * artefact first and the person last, so a bio reads as an answer rather than
 * an opening boast.
 */
export const MAKER_SHORT =
  "The product calls and the standard are mine. The typing is theirs. ModelDeck, Panely and HiveRunner were all built that way, and so was this catalog — every skill here started as a workflow I got tired of re-explaining at the top of every session.";

/** The long form, for /work. Two paragraphs: why the catalog exists, then who. */
export const MAKER_LONG = [
  "I ship software by directing AI agents. The product calls, the standard, and the last read before anything ships are mine; the implementation is delegated and then reviewed. Every build on this page was made that way, and this catalog is that method written down — a skill here is a workflow that survived enough sessions to be worth keeping.",
  "Before this: a full wrestling scholarship at the University of Minnesota, twice an All-American, and a stretch training at an Olympic centre in Russia while still in high school. Then a Series 7 and a few years as a stockbroker. I have run my own company since 2011 — Insight builds decisioning software for consumer lenders. Grew up in St. Louis. Live in Healdsburg, California.",
];
