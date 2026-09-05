import { getSkills } from "@/lib/skills";
import { skillMarkdown } from "@/lib/skill-markdown";

export const dynamic = "force-static";

export function generateStaticParams() {
  return getSkills().map((skill) => ({ slug: skill.slug }));
}

export async function GET(_request: Request, context: { params: Promise<{ slug: string }> }) {
  const { slug } = await context.params;
  return skillMarkdown(slug, "claude");
}
