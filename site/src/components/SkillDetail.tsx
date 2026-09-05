import Link from "next/link";
import { notFound } from "next/navigation";
import { marked } from "marked";
import Terminal from "@/components/Terminal";
import { getCodexPlugin, getEditionSkill, getBuckets, type Edition } from "@/lib/skills";
import { editionHuman } from "@/lib/human";
import { INVOCATION, invocationLabel } from "@/lib/catalog";

/**
 * SKILL.md links are relative to the skill's own directory, so they only
 * resolve on GitHub. Rewrite them there rather than shipping dead links.
 *
 * Resolved against `skills/<bucket>/<slug>/`, not `skills/<slug>/` — skills
 * moved into buckets and every one of these links pointed at a 404 until this
 * took the bucket into account. `..` segments are collapsed rather than
 * stripped, so a link out of a skill's own directory lands where it means to.
 */
function absolutise(html: string, bucket: string, slug: string, edition: Edition): string {
  const root = "https://github.com/timharris707/skills/blob/main";
  const from = [...(edition === "codex" ? ["plugins", "clickai-codex"] : []), "skills", bucket, slug];

  return html.replace(/href="(?!https?:|\/|#|mailto:)([^"]+)"/g, (_m, href: string) => {
    const segments = [...from];
    for (const part of href.split("/")) {
      if (part === "..") segments.pop();
      else if (part !== "." && part !== "") segments.push(part);
    }
    return `href="${root}/${segments.join("/")}"`;
  });
}

export default async function SkillDetail({ slug, edition }: { slug: string; edition: Edition }) {
  const skill = getEditionSkill(slug, edition);
  if (!skill) notFound();

  const region = getBuckets().find((b) => b.id === skill.bucket);
  // The SKILL.md H1 is the page title, so drop it rather than printing it twice.
  const body = skill.body.trimStart().replace(/^#\s+.*(\r?\n|$)/, "");
  const html = absolutise(await marked.parse(body), skill.bucket, skill.slug, edition);
  const codex = getCodexPlugin();
  // Who invokes it, from the CI-synced INVOCATION map (frontmatter is the
  // source of truth; check_invocation_freshness.py polices the sync).
  const invocation = edition === "claude" ? INVOCATION[skill.slug] : undefined;

  return (
    <div className="shell detail">
      <article>
        <Link href="/skills" className="crumb">
          ← Catalog {region ? `/ ${region.name}` : ""}
        </Link>
        <nav aria-label="Skill edition" className="edition-switch">
          <Link href={`/skills/${slug}`} aria-current={edition === "claude" ? "page" : undefined}>Claude Code</Link>
          <Link href={`/codex/skills/${slug}`} aria-current={edition === "codex" ? "page" : undefined}>Codex desktop</Link>
        </nav>
        <h1 className="detail__title">{skill.name}</h1>
        {/* The human intro, from src/lib/human.ts. The agent's own wording —
            description, triggers, the full document — is one flip away and
            rendered below; this paragraph is the page's only copy written for
            a reader who doesn't code. */}
        <p className="detail__claim" style={{ fontSize: "1.05rem", maxWidth: "var(--measure)", margin: "0.5rem 0 1rem" }}>
          {editionHuman(skill.slug, edition).intro}
        </p>
        <div className="prose" dangerouslySetInnerHTML={{ __html: html }} />
      </article>

      <aside className="aside">
        <h3>Install</h3>
        <Terminal
          lines={edition === "codex" ? [
            { command: `codex plugin add ${codex.name}@${codex.marketplace}`, comment: "Codex desktop" },
          ] : [
            { command: `/plugin install ${skill.plugin}@skills`, comment: "Claude Code" },
          ]}
        />
        <p><Link href={`/install#${edition}`}>First install and edition guidance →</Link></p>

        <h3>Details</h3>
        <dl>
          <dt>Ships in</dt>
          <dd>
            {skill.plugin}
            {skill.pluginVersion ? ` v${skill.pluginVersion}` : ""}
          </dd>
          <dt>Region</dt>
          <dd>{region?.name ?? "—"}</dd>
          {invocation && (
            <>
              <dt>Invoked</dt>
              <dd>
                {invocationLabel(invocation.invokedBy)}
                {invocation.command ? (
                  <>
                    {" "}
                    (<code>{invocation.command}</code>)
                  </>
                ) : null}
              </dd>
            </>
          )}
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
