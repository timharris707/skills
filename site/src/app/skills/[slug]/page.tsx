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
 * One subject-claim sentence per skill — "x is a skill that …" — so the page
 * answers what the thing IS before the "Use when" triggers fire. Site-side on
 * purpose: SKILL.md descriptions open with an imperative for the agent reading
 * them, and this page is read by humans. Each sentence paraphrases the skill's
 * own description and must stay checkable against it. A skill missing here
 * falls back to its description's first sentence — add a claim when a skill
 * lands in a promoted bucket.
 */
const SUBJECT_CLAIMS: Record<string, string> = {
  router:
    "router is a skill that gives a session one entry point to the team-workflow pack: it names every skill and when to reach for each.",
  setup:
    "setup is a skill that binds the team-workflow pack to a repo through a one-time interview: how you test, where work is tracked, who has the final say.",
  "domain-memory":
    "domain-memory is a skill that keeps a repo's institutional memory as a side effect of ordinary work: what its words mean, and why its settled decisions went the way they did.",
  grilling:
    "grilling is a skill that has the agent interview you, round after round, until nothing load-bearing in a plan is still assumed.",
  "advisory-board":
    "advisory-board is a skill that convenes frontier models from four vendors on one question and returns a single verdict with the dissent preserved.",
  "decision-map":
    "decision-map is a skill that charts genuinely foggy work as a map of gated decisions and works it until nothing gating is undecided.",
  ingest:
    "ingest is a skill that turns a video, recording, or voice memo into an evidence packet (transcript, timestamped frames, manifest) plus a recommendation for where it enters the work.",
  research:
    "research is a skill that runs an autonomous investigation against primary sources and ends in a cited findings file linked from the ticket that asked.",
  prototype:
    "prototype is a skill that builds throwaway code to answer a design question that discussion and static artifacts cannot settle.",
  "codebase-review":
    "codebase-review is a skill that reviews the state of the codebase between changes, the counterpart to adversarial-review's review of a single change.",
  diagnose:
    "diagnose is a skill that holds bug-fixing to a disciplined loop: no fix ships without a cause the fixer can state in one plain sentence, with evidence.",
  implement:
    "implement is a skill that disciplines how a working session builds an item, test-first and in thin slices that go end to end, with a green checkpoint after each.",
  "to-tickets":
    "to-tickets is a skill that turns a decided plan into tracker items a stranger could pick up cold, with their blocking edges wired.",
  wizard:
    "wizard is a skill that generates an interactive walkthrough for the steps only a human can perform, from third-party dashboards to credentials to DNS records.",
  orchestrate:
    "orchestrate is a skill that turns one session into the coordinator of many, routing tracked work to parallel sessions, auditing what comes back, and owning integration.",
  "adversarial-review":
    "adversarial-review is a skill that tries to break a change before it ships: isolated finders attack it, a skeptic pass kills unproven findings, and confirmed blockers gate the merge.",
  handoff:
    "handoff is a skill that writes where the work stands into one small file, so a fresh session resumes without re-explanation.",
  "writing-for-agents":
    "writing-for-agents is a skill that writes and prunes the documents agents consume: SKILL.md files, standing instructions, reference files.",
  "writing-for-humans":
    "writing-for-humans is a skill that makes public-facing prose worth a stranger's next minute through guide shape, observable warmth, and a last-mile scrub for AI tells.",
  huh: "huh is a skill that decodes an agent message that didn't land: a plain-sentence restatement, invented shorthand expanded, the ask separated from the report, and unevidenced claims flagged.",
};

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
        <p className="detail__claim" style={{ fontSize: "1.05rem", maxWidth: "var(--measure)", margin: "0.5rem 0 1rem" }}>
          {SUBJECT_CLAIMS[skill.slug] ?? summarize(skill.description)}
        </p>
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
