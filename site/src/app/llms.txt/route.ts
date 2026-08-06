import { getCatalog } from "@/lib/catalog";
import { getCodexPlugin, getPlugins } from "@/lib/skills";

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
    "# Click AI — portable skills for AI agents",
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
    "## Formats",
    "",
    "- Append `.md` to any skill URL for its full SKILL.md.",
    "- https://clickai.dev/skills — the catalog.",
    "- https://clickai.dev/sitemap.xml — every page.",
    "",
  );

  return new Response(lines.join("\n"), {
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}
