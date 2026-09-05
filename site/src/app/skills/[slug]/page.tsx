import type { Metadata } from "next";
import { openGraph } from "@/lib/meta";
import { getSkill, getSkills } from "@/lib/skills";
import { human } from "@/lib/human";
import SkillDetail from "@/components/SkillDetail";

type Params = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return getSkills().map((skill) => ({ slug: skill.slug }));
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug } = await params;
  const skill = getSkill(slug);
  if (!skill) return {};
  return {
    title: skill.name,
    description: human(skill.slug).card,
    alternates: { canonical: `/skills/${skill.slug}` },
    openGraph: openGraph(`/skills/${skill.slug}`),
  };
}

export default async function SkillPage({ params }: Params) {
  const { slug } = await params;
  return <SkillDetail slug={slug} edition="claude" />;
}
