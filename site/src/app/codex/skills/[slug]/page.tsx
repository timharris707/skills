import type { Metadata } from "next";
import { openGraph } from "@/lib/meta";
import { getEditionSkill, getSkills } from "@/lib/skills";
import { editionHuman } from "@/lib/human";
import SkillDetail from "@/components/SkillDetail";

type Params = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return getSkills().map((skill) => ({ slug: skill.slug }));
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug } = await params;
  const skill = getEditionSkill(slug, "codex");
  if (!skill) return {};
  return {
    title: `${skill.name} for Codex`,
    description: editionHuman(slug, "codex").card,
    alternates: { canonical: `/codex/skills/${slug}` },
    openGraph: openGraph(`/codex/skills/${slug}`),
  };
}

export default async function CodexSkillPage({ params }: Params) {
  const { slug } = await params;
  return <SkillDetail slug={slug} edition="codex" />;
}
