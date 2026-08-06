import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { marked } from "marked";
import { KIND_LABEL, formatDate, getNote, getNotes } from "@/lib/notes";

type Params = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return getNotes().map((note) => ({ slug: note.slug }));
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug } = await params;
  const note = getNote(slug);
  if (!note) return {};
  return {
    title: note.title,
    description: note.standfirst,
    alternates: { canonical: `/notes/${note.slug}` },
    openGraph: { type: "article", publishedTime: note.date },
  };
}

export default async function NotePage({ params }: Params) {
  const { slug } = await params;
  const note = getNote(slug);
  if (!note) notFound();

  const html = await marked.parse(note.body);

  return (
    <div className="shell detail">
      <article>
        <Link href="/notes" className="crumb">
          ← Notes / {KIND_LABEL[note.kind]}
        </Link>
        <h1 className="note__title">{note.title}</h1>
        <p className="detail__trigger">{note.standfirst}</p>
        <div className="prose" dangerouslySetInnerHTML={{ __html: html }} />
      </article>

      <aside className="aside">
        <h3>This note</h3>
        <dl>
          <dt>Kind</dt>
          <dd>{KIND_LABEL[note.kind]}</dd>
          <dt>Published</dt>
          <dd>{formatDate(note.date)}</dd>
          {note.checked ? (
            <>
              <dt>Claims last checked</dt>
              <dd>{formatDate(note.checked)}</dd>
            </>
          ) : null}
          <dt>Reading</dt>
          <dd>{note.minutes} min</dd>
          <dt>Markdown</dt>
          <dd>
            <a href={`/notes/${note.slug}.md`}>{note.slug}.md</a>
          </dd>
        </dl>

        {/* A survey's credibility is the freshness of its claims, so the date
            it was last re-checked belongs on the page, not just in a feed. */}
        {note.checked ? (
          <p className="aside__note" style={{ marginTop: "1.4rem" }}>
            Dated claims here are re-verified on review. If one has gone stale, it gets a{" "}
            <Link href="/notes">Correction</Link> of its own rather than a silent edit.
          </p>
        ) : null}
      </aside>
    </div>
  );
}
