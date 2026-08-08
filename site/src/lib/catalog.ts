import { getBuckets, getSkills, type Bucket, type Skill } from "./skills";

/**
 * The catalog's regions ARE the repository's promoted buckets — name, order,
 * and blurb all come from `skills/buckets.json`, so a skill's category is the
 * directory it sits in and there is no second list to keep in step.
 *
 * What stays hand-maintained here is the one thing a directory cannot express:
 * where each skill plots on the hero chart, and which handoffs to draw between
 * them. `assertComplete` fails the build when a skill has no plot position —
 * the same enforcement `scripts/check_router_freshness.py` applies to the
 * marketplace and the router.
 */

export type Region = Bucket & { entries: Skill[] };

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
  ingest: { x: 445, y: 95 },
  research: { x: 445, y: 375 },
  "codebase-review": { x: 445, y: 295 },
  prototype: { x: 445, y: 475 },
  "to-tickets": { x: 655, y: 290 },
  wizard: { x: 655, y: 415 },
  orchestrate: { x: 830, y: 190 },
  "adversarial-review": { x: 830, y: 320, anchor: "end" },
  handoff: { x: 830, y: 430 },
  "writing-for-agents": { x: 940, y: 490, anchor: "end" },
};

/**
 * How the skills actually compose. Most edges are handoffs a SKILL.md states
 * outright; two — advisory-board → decision-map and wizard → orchestrate — are
 * compositions the pack supports that no SKILL.md names, so they are asserted
 * here rather than quoted from there. None is a decorative line.
 *
 * Worth keeping straight, because /notes/graph-engineering cites this graph:
 * it records which skill hands off to which, not what blocks what. That makes
 * it an org graph, not a task graph.
 */
export const BEARINGS: Array<{ from: string; to: string; note: string }> = [
  { from: "setup", to: "grilling", note: "bindings first" },
  { from: "router", to: "grilling", note: "start here" },
  { from: "grilling", to: "decision-map", note: "map-sized" },
  { from: "grilling", to: "to-tickets", note: "pressure-tested" },
  { from: "ingest", to: "grilling", note: "undecided takeaways" },
  { from: "ingest", to: "to-tickets", note: "ticket-shaped takeaways" },
  { from: "advisory-board", to: "decision-map", note: "test a position" },
  { from: "decision-map", to: "research", note: "research ticket" },
  { from: "decision-map", to: "prototype", note: "prototype ticket" },
  { from: "decision-map", to: "to-tickets", note: "decided" },
  { from: "research", to: "to-tickets", note: "findings" },
  { from: "prototype", to: "to-tickets", note: "the verdict" },
  { from: "to-tickets", to: "orchestrate", note: "into lanes" },
  { from: "wizard", to: "orchestrate", note: "human-only steps" },
  { from: "orchestrate", to: "adversarial-review", note: "lane close-out" },
  { from: "orchestrate", to: "codebase-review", note: "state review" },
  { from: "codebase-review", to: "to-tickets", note: "adopted survivors" },
  { from: "orchestrate", to: "handoff", note: "context fills" },
];

export type PlacedSkill = Skill & { region: Region };

/**
 * A skill's region is settled by its directory, so the only thing left to check
 * is that the chart knows where to draw it. Throwing here fails `next build`,
 * which is the point: a skill with no position would silently vanish from the
 * hero while still appearing in its region list.
 */
function assertComplete(skills: Skill[]) {
  const unplotted = skills.filter((s) => !PLOT[s.slug]).map((s) => s.slug);
  if (unplotted.length) {
    throw new Error(
      `catalog.ts: ${unplotted.join(", ")} ${unplotted.length === 1 ? "has" : "have"} no PLOT ` +
        "position for the hero chart. Add a position in src/lib/catalog.ts.",
    );
  }

  const known = new Set(skills.map((s) => s.slug));
  const ghosts = Object.keys(PLOT).filter((slug) => !known.has(slug));
  if (ghosts.length) {
    throw new Error(
      `catalog.ts: ${ghosts.join(", ")} plotted on the chart but not in any promoted bucket — ` +
        "remove the PLOT entry, or promote the skill.",
    );
  }

  const plotted = new Set(known);
  const dangling = BEARINGS.filter((b) => !plotted.has(b.from) || !plotted.has(b.to));
  if (dangling.length) {
    throw new Error(
      `catalog.ts: bearing(s) reference skills that are not in a promoted bucket: ` +
        dangling.map((b) => `${b.from} → ${b.to}`).join(", "),
    );
  }
}

export function getCatalog(): { regions: Region[]; skills: PlacedSkill[] } {
  const skills = getSkills();
  assertComplete(skills);

  const regions = getBuckets()
    .filter((b) => b.promoted)
    .map((bucket) => ({
      ...bucket,
      entries: skills.filter((s) => s.bucket === bucket.id),
    }))
    .filter((region) => region.entries.length > 0);

  const byId = new Map(regions.map((r) => [r.id, r]));
  const placed = skills.map((skill) => ({ ...skill, region: byId.get(skill.bucket)! }));

  return { regions, skills: placed };
}
