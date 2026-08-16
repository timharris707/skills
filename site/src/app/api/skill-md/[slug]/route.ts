import { getCodexPlugin, getSkill, getSkills } from "@/lib/skills";

export const dynamic = "force-static";

/** Indent a set of commands and line their trailing comments up. */
function alignComments(rows: Array<[string, string]>): string[] {
  const width = Math.max(...rows.map(([cmd]) => cmd.length));
  return rows.map(([cmd, note]) => `    ${cmd.padEnd(width)}   # ${note}`);
}

export function generateStaticParams() {
  return getSkills().map((skill) => ({ slug: skill.slug }));
}

/**
 * The Markdown twin behind `/skills/<name>.md` (see the rewrite in
 * next.config.ts): the SKILL.md an agent would install, served raw so fetching
 * the page an engineer is reading returns exactly what ships.
 */
export async function GET(_request: Request, context: { params: Promise<{ slug: string }> }) {
  const { slug } = await context.params;
  const skill = getSkill(slug);
  if (!skill) return new Response("Not found\n", { status: 404 });
  const codex = getCodexPlugin();

  const source = [
    "---",
    `name: ${skill.name}`,
    `description: ${skill.description}`,
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
    "Runs natively on both Claude Code and Codex, from this same file:",
    "",
    ...alignComments([
      [`/plugin install ${skill.plugin}@skills`, "Claude Code"],
      [`codex plugin add ${codex.name}@${codex.marketplace}`, "Codex"],
    ]),
    "",
    "Agents: do not save this file as a loose skill in the user's config — loose copies",
    "drop the bundled files, the pack wiring, and all updates. With shell access, run",
    `\`claude plugin marketplace add timharris707/skills\` then \`claude plugin install ${skill.plugin}@skills\`;`,
    "otherwise relay the commands above to your user.",
    "",
    "Any other harness can read this SKILL.md directly.",
    "",
  ].join("\n");

  return new Response(source, {
    headers: { "content-type": "text/markdown; charset=utf-8" },
  });
}
