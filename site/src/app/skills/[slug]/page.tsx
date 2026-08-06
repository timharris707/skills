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
 *
 * Resolved against `skills/<bucket>/<slug>/`, not `skills/<slug>/` — skills
 * moved into buckets and every one of these links pointed at a 404 until this
 * took the bucket into account. `..` segments are collapsed rather than
 * stripped, so a link out of a skill's own directory lands where it means to.
 */
function absolutise(html: string, bucket: string, slug: string): string {
  const root = "https://github.com/timharris707/skills/blob/main";
  const from = ["skills", bucket, slug];

  return html.replace(/href="(?!https?:|\/|#|mailto:)([^"]+)"/g, (_m, href: string) => {
    const segments = [...from];
    for (const part of href.split("/")) {
      if (part === "..") segments.pop();
      else if (part !== "." && part !== "") segments.push(part);
    }
    return `href="${root}/${segments.join("/")}"`;
  });
}

export default async function SkillPage({ params }: Params) {
  const { slug } = await params;
  const skill = getSkill(slug);
  if (!skill) notFound();

  const region = getBuckets().find((b) => b.id === skill.bucket);
  // The SKILL.md H1 is the page title, so drop it rather than printing it twice.
  const body = skill.body.trimStart().replace(/^#\s+.*(\r?\n|$)/, "");
  const html = absolutise(await marked.parse(body), skill.bucket, skill.slug);
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
