import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { marked } from "marked";
import Terminal from "@/components/Terminal";
import Runtimes from "@/components/Runtimes";
import { getCodexPlugin, getSkill, getSkills, summarize } from "@/lib/skills";
import { getBuckets } from "@/lib/skills";

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
    description: summarize(skill.description),
    alternates: { canonical: `/skills/${skill.slug}` },
  };
}

/** The "Use when …" clause — the triggers that decide when a skill fires. */
function trigger(description: string): string | null {
  const match = description.match(/\b(Use when|Use for)\b.*/s);
  return match ? match[0].trim() : null;
}

/**
 * SKILL.md links are relative to the skill's own directory, so they only
 * resolve on GitHub. Rewrite them there rather than shipping dead links.
 */
function absolutise(html: string, slug: string): string {
  const base = `https://github.com/timharris707/skills/blob/main/skills/${slug}/`;
  return html.replace(/href="(?!https?:|\/|#|mailto:)([^"]+)"/g, (_m, href) => {
    const target = href.startsWith("../")
      ? `https://github.com/timharris707/skills/blob/main/skills/${href.slice(3)}`
      : `${base}${href}`;
    return `href="${target}"`;
  });
}

export default async function SkillPage({ params }: Params) {
  const { slug } = await params;
  const skill = getSkill(slug);
  if (!skill) notFound();

  const region = getBuckets().find((b) => b.id === skill.bucket);
  // The SKILL.md H1 is the page title, so drop it rather than printing it twice.
  const body = skill.body.trimStart().replace(/^#\s+.*(\r?\n|$)/, "");
  const html = absolutise(await marked.parse(body), skill.slug);
  const useWhen = trigger(skill.description);
  const codex = getCodexPlugin();

  return (
    <div className="shell detail">
      <article>
        <Link href="/skills" className="crumb">
          ← Catalog {region ? `/ ${region.name}` : ""}
        </Link>
        <h1 className="detail__title">{skill.name}</h1>
        <p className="detail__trigger">{useWhen ?? summarize(skill.description)}</p>
        <div className="prose" dangerouslySetInnerHTML={{ __html: html }} />
      </article>

      <aside className="aside">
        <h3>Install</h3>
        <Terminal
          lines={[
            { command: `/plugin install ${skill.plugin}@skills`, comment: "Claude Code" },
            { command: `codex plugin add ${codex.name}@${codex.marketplace}`, comment: "Codex" },
          ]}
        />
        <Runtimes lead="Runs on" />

        <h3>Details</h3>
        <dl>
          <dt>Ships in</dt>
          <dd>
            {skill.plugin}
            {skill.pluginVersion ? ` v${skill.pluginVersion}` : ""}
          </dd>
          <dt>Region</dt>
          <dd>{region?.name ?? "—"}</dd>
          <dt>Source</dt>
          <dd>
            <a href={skill.githubUrl}>SKILL.md</a>
          </dd>
        </dl>

        {skill.extras.length > 0 && (
          <>
            <h3>Also ships</h3>
            <ul>
              {skill.extras.map((file) => (
                <li key={file}>{file}</li>
              ))}
            </ul>
          </>
        )}
      </aside>
    </div>
  );
}
