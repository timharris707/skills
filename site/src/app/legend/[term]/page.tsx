import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { BANDS, ENTRIES, getEntry } from "@/lib/legend";
import { getSkill, summarize } from "@/lib/skills";

type Params = { params: Promise<{ term: string }> };

export function generateStaticParams() {
  return ENTRIES.map((entry) => ({ term: entry.slug }));
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { term } = await params;
  const entry = getEntry(term);
  if (!entry) return {};
  return {
    title: entry.term,
    description: entry.gloss,
    alternates: { canonical: `/legend/${entry.slug}` },
  };
}

export default async function LegendTerm({ params }: Params) {
  const { term } = await params;
  const entry = getEntry(term);
  if (!entry) notFound();

  const skill = entry.skill ? getSkill(entry.skill) : undefined;
  const related = (entry.seeAlso ?? []).map((s) => getEntry(s)).filter(Boolean);

  return (
    <div className="shell detail">
      <article>
        <Link href="/legend" className="crumb">
          ← Legend / {entry.group}
        </Link>
        <h1 className="detail__title">{entry.term}</h1>

        <p className="term__band">
          <span className={`band band--${entry.band}`}>{entry.band}</span>
          <span>{entry.bandClaim ?? BANDS[entry.band]}</span>
        </p>

        <div className="prose">
          <p style={{ fontSize: "1.06rem" }}>{entry.definition}</p>
        </div>
      </article>

      <aside className="aside">
        {skill ? (
          <>
            <h3>Implemented by</h3>
            <p className="term__skill">
              <Link href={`/skills/${skill.slug}`}>{skill.name}</Link>
              <span>{summarize(skill.description)}</span>
            </p>
          </>
        ) : null}

        {related.length > 0 ? (
          <>
            <h3>See also</h3>
            <ul>
              {related.map((r) => (
                <li key={r!.slug}>
                  <Link href={`/legend/${r!.slug}`}>{r!.term}</Link>
                </li>
              ))}
            </ul>
          </>
        ) : null}

        <h3>This entry</h3>
        <dl>
          <dt>Group</dt>
          <dd>{entry.group}</dd>
          <dt>Markdown</dt>
          <dd>
            <a href={`/legend/${entry.slug}.md`}>{entry.slug}.md</a>
          </dd>
        </dl>
      </aside>
    </div>
  );
}
