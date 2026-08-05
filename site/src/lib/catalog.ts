import { getSkills, type Skill } from "./skills";

/**
 * Editorial layer over the generated catalog: which region a skill sits in, and
 * where it plots on the hero chart.
 *
 * This file is deliberately the one hand-maintained surface, and `assertComplete`
 * fails the build when a new skill is not placed — the same enforcement the repo
 * uses for router freshness. A silently uncategorised skill is worse than a
 * broken build: it ships, and nobody finds it.
 */

export type Region = {
  id: string;
  name: string;
  blurb: string;
  skills: string[];
};

export const REGIONS: Region[] = [
  {
    id: "orient",
    name: "Orient",
    blurb: "Bind the discipline to a repo, and find your way around it.",
    skills: ["router", "setup"],
  },
  {
    id: "decide",
    name: "Decide",
    blurb: "Settle what is still open before anyone writes a line of it.",
    skills: ["grilling", "decision-map", "advisory-board"],
  },
  {
    id: "investigate",
    name: "Investigate",
    blurb: "Answer what discussion cannot — from sources, or from running code.",
    skills: ["research", "prototype"],
  },
  {
    id: "run",
    name: "Run",
    blurb: "Get decided work onto the board, through the lanes, and handed on.",
    skills: ["to-tickets", "wizard", "orchestrate", "handoff"],
  },
  {
    id: "author",
    name: "Author",
    blurb: "The standard the rest of this catalog is written against.",
    skills: ["writing-for-agents"],
  },
];

/**
 * Plotted positions on the hero chart, in a 1000×520 viewBox. Left to right is
 * the order work moves: orient, decide, investigate, run. The right-hand column
 * letters its labels leftwards so nothing runs off the chart.
 */
export const PLOT: Record<string, { x: number; y: number; anchor?: "start" | "end" }> = {
  router: { x: 70, y: 90 },
  setup: { x: 70, y: 200 },
  grilling: { x: 255, y: 145 },
  "advisory-board": { x: 255, y: 320 },
  "decision-map": { x: 445, y: 215 },
  research: { x: 445, y: 375 },
  prototype: { x: 445, y: 475 },
  "to-tickets": { x: 655, y: 290 },
  wizard: { x: 655, y: 415 },
  orchestrate: { x: 830, y: 190 },
  handoff: { x: 830, y: 320 },
  "writing-for-agents": { x: 940, y: 490, anchor: "end" },
};

/**
 * How the skills actually compose — each edge is a real handoff documented in
 * one of the SKILL.md files, not a decorative line.
 */
export const BEARINGS: Array<{ from: string; to: string; note: string }> = [
  { from: "setup", to: "grilling", note: "bindings first" },
  { from: "router", to: "grilling", note: "start here" },
  { from: "grilling", to: "decision-map", note: "map-sized" },
  { from: "grilling", to: "to-tickets", note: "pressure-tested" },
  { from: "advisory-board", to: "decision-map", note: "test a position" },
  { from: "decision-map", to: "research", note: "research ticket" },
  { from: "decision-map", to: "prototype", note: "prototype ticket" },
  { from: "decision-map", to: "to-tickets", note: "decided" },
  { from: "research", to: "to-tickets", note: "findings" },
  { from: "prototype", to: "to-tickets", note: "the verdict" },
  { from: "to-tickets", to: "orchestrate", note: "into lanes" },
  { from: "wizard", to: "orchestrate", note: "human-only steps" },
  { from: "orchestrate", to: "handoff", note: "context fills" },
];

export type PlacedSkill = Skill & { region: Region };

/**
 * Every skill on disk must be placed in a region and plotted on the chart.
 * Throwing here fails `next build`, which is the point.
 */
function assertComplete(skills: Skill[]) {
  const placed = new Set(REGIONS.flatMap((r) => r.skills));
  const missing = skills.filter((s) => !placed.has(s.slug)).map((s) => s.slug);
  if (missing.length) {
    throw new Error(
      `catalog.ts: ${missing.join(", ")} ${missing.length === 1 ? "is" : "are"} not in any region. ` +
        `Add ${missing.length === 1 ? "it" : "them"} to REGIONS and PLOT in src/lib/catalog.ts.`,
    );
  }

  const known = new Set(skills.map((s) => s.slug));
  const ghosts = [...placed].filter((slug) => !known.has(slug));
  if (ghosts.length) {
    throw new Error(`catalog.ts: ${ghosts.join(", ")} listed in REGIONS but not present in skills/.`);
  }

  const unplotted = skills.filter((s) => !PLOT[s.slug]).map((s) => s.slug);
  if (unplotted.length) {
    throw new Error(`catalog.ts: ${unplotted.join(", ")} has no PLOT position for the hero chart.`);
  }
}

export function getCatalog(): { regions: Array<Region & { entries: Skill[] }>; skills: PlacedSkill[] } {
  const skills = getSkills();
  assertComplete(skills);

  const bySlug = new Map(skills.map((s) => [s.slug, s]));
  const regions = REGIONS.map((region) => ({
    ...region,
    entries: region.skills.map((slug) => bySlug.get(slug)!),
  }));

  const placed = skills.map((skill) => ({
    ...skill,
    region: REGIONS.find((r) => r.skills.includes(skill.slug))!,
  }));

  return { regions, skills: placed };
}
