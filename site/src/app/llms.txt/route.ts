import { getCatalog } from "@/lib/catalog";
import { ENTRIES } from "@/lib/legend";
import { KIND_LABEL, getNotes } from "@/lib/notes";
import { getCodexPlugin, getPlugins } from "@/lib/skills";
import { BUILD_COUNT, PRIVATE_COUNT } from "@/lib/work";

export const dynamic = "force-static";

/**
 * The catalog as one file an agent can read in a single fetch — the same
 * orientation surface aihero.dev exposes, generated from the same SKILL.md
 * files the site renders.
 */
export function GET() {
  const { regions, skills } = getCatalog();
  const plugins = getPlugins();
  const codex = getCodexPlugin();

  const lines = [
    "# Click AI — the method that let a non-coder ship four products",
    "",
    "> Self-contained playbooks any AI agent can read. Each skill is a SKILL.md plus the",
    "> templates and scripts it needs. Source: https://github.com/timharris707/skills (MIT).",
    "",
    `${skills.length} skills in ${regions.length} regions.`,
    "",
    "## Runtimes",
    "",
    "Every skill runs natively on BOTH Claude Code and Codex, from the same SKILL.md.",
    "Neither is a port or a second-class path: the instructions are the portable part,",
    "and CI fails the build if the two runtimes would ship a different set of skills.",
    "Any other harness can read each SKILL.md directly.",
    "",
    "## Install — Claude Code",
    "",
    "```",
    "/plugin marketplace add timharris707/skills",
    ...plugins.map((p) => `/plugin install ${p.name}@skills`),
    "```",
    "",
    "## Install — Codex",
    "",
    "Codex allows one plugin per repository root, so the whole catalog is a single plugin.",
    "",
    "```",
    "codex plugin marketplace add timharris707/skills",
    `codex plugin add ${codex.name}@${codex.marketplace}`,
    "```",
    "",
  ];

  for (const region of regions) {
    lines.push(`## ${region.name}`, "", region.blurb, "");
    for (const skill of region.entries) {
      lines.push(
        `- [${skill.name}](https://clickai.dev/skills/${skill.slug}.md): ${skill.description}`,
      );
    }
    lines.push("");
  }

  lines.push(
    "## Legend — the vocabulary",
    "",
    `${ENTRIES.length} terms from agentic coding, each graded for how solid the claim is and`,
    "cross-linked to the skill that implements it where one does. Where a term is",
    "mostly a rebrand, the entry says so.",
    "",
    "- https://clickai.dev/legend.md — every definition in one fetch.",
    "- https://clickai.dev/legend/<term>.md — a single entry.",
    "",
    "## Notes",
    "",
    "Surveys, corrections and catalog releases. A correction is always a new note,",
    "never a silent edit.",
    "",
    ...getNotes().map(
      (n) =>
        `- [${KIND_LABEL[n.kind]}: ${n.title}](https://clickai.dev/notes/${n.slug}.md) — ${n.standfirst}`,
    ),
    "",
    "## Instruments",
    "",
    "The tools these skills are run with, none of them sponsored: Fallow and CodeGraph",
    "for structural ground truth, CodeRabbit as a second reader, CLIProxyAPI and ModelDeck",
    "for capacity. Every entry states where the tool stops.",
    "",
    "- https://clickai.dev/instruments.md",
    "",
    "## Who makes this",
    "",
    "Tim Harris. Product and direction are his; agents do the implementation, and he",
    `reviews it. ${BUILD_COUNT} builds on the same method — ModelDeck, Panely, HiveRunner and this`,
    `catalog are public; ${PRIVATE_COUNT} are private. Full detail: https://clickai.dev/work.md`,
    "",
    "## Formats",
    "",
    "- Append `.md` to any skill, legend or note URL for its markdown twin.",
    "- https://clickai.dev/skills — the catalog.",
    "- https://clickai.dev/legend.md — the vocabulary, in one fetch.",
    "- https://clickai.dev/work.md — the builds behind it, and the maker.",
    "- https://clickai.dev/instruments.md — the tools it is run with.",
    "- https://clickai.dev/rss.xml — new notes.",
    "- https://clickai.dev/sitemap.xml — every page.",
    "",
  );

  return new Response(lines.join("\n"), {
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}
