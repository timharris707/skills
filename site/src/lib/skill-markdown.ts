import { getCodexPlugin, getEditionSkill, type Edition } from "@/lib/skills";

export function skillMarkdown(slug: string, edition: Edition): Response {
  const skill = getEditionSkill(slug, edition);
  if (!skill) return new Response("Not found\n", { status: 404 });
  const codex = getCodexPlugin();
  const source = [
    "---",
    `name: ${skill.name}`,
    // JSON string quoting is valid YAML, so the twin's frontmatter stays
    // parseable even when the description contains colons or quotes.
    `description: ${JSON.stringify(skill.description)}`,
    "---",
    "",
    skill.body.trimStart(),
    "",
    "---",
    "",
    `Ships in: ${skill.plugin}${skill.pluginVersion ? ` v${skill.pluginVersion}` : ""}`,
    `Source: ${skill.githubUrl}`,
    ...(skill.extras.length ? [`Also ships: ${skill.extras.join(", ")}`] : []),
    "",
    edition === "codex" ? "Codex desktop edition, adapted for Astra workflows. Install the complete plugin:" : "Claude Code edition. Install its complete plugin:",
    "",
    ...(edition === "codex" ? [
      "    codex plugin marketplace add timharris707/skills",
      `    codex plugin add ${codex.name}@${codex.marketplace}`,
      "",
      "Start a new task after installation. Disable the legacy clickai-skills plugin",
      "in this Codex profile if installed, to avoid duplicate skill names.",
      "This edition changes no global instructions, model settings, or Claude configuration.",
    ] : [
      "    claude plugin marketplace add timharris707/skills",
      `    claude plugin install ${skill.plugin}@skills`,
    ]),
    "",
    "Install the complete plugin; a loose SKILL.md omits its templates and scripts.",
    "",
    `Other edition: https://clickai.dev/${edition === "codex" ? "" : "codex/"}skills/${skill.slug}.md`,
    "Install and update guidance: https://clickai.dev/install",
    "",
  ].join("\n");

  return new Response(source, { headers: { "content-type": "text/markdown; charset=utf-8" } });
}
