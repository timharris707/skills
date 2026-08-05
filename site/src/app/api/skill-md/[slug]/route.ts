import { getSkill, getSkills } from "@/lib/skills";

export const dynamic = "force-static";

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
  ].join("\n");

  return new Response(source, {
    headers: { "content-type": "text/markdown; charset=utf-8" },
  });
}
