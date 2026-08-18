import type { Metadata } from "next";
import { openGraph } from "@/lib/meta";
import Link from "next/link";
import { notFound } from "next/navigation";
import { marked } from "marked";
import { KIND_LABEL, formatDate, getNote, getNotes } from "@/lib/notes";
import { articleNode, graph, jsonLdProps, PERSON } from "@/lib/schema";

type Params = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return getNotes().map((note) => ({ slug: note.slug }));
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug } = await params;
  const note = getNote(slug);
  if (!note) return {};
  return {
    // The kind is part of the title because a note and a legend entry can share
    // a subject — "Graph engineering" was both, under one identical title, and
    // neither a reader nor a crawler could tell which page they had landed on.
    title: `${note.title} — ${KIND_LABEL[note.kind]}`,
    description: note.standfirst,
    alternates: { canonical: `/notes/${note.slug}` },
    // Not the shared helper: notes are articles, not website pages. siteName
    // and url still need restating here — this block replaces the layout's.
    openGraph: {
      type: "article",
      siteName: "Click AI",
      url: `/notes/${note.slug}`,
      publishedTime: note.date,
      modifiedTime: note.checked ?? note.date,
      authors: ["Tim Harris"],
    },
  };
}

export default async function NotePage({ params }: Params) {
  const { slug } = await params;
  const note = getNote(slug);
  if (!note) notFound();

  const html = await marked.parse(note.body);

  return (
    <div className="shell detail">
      <script {...jsonLdProps(graph(PERSON, articleNode(note)))} />
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
          {/* The <time> wrapper is the same date the reader sees, in the form a
              crawler can parse. Without it the page is undated to a machine. */}
          <dd>
            <time dateTime={note.date}>{formatDate(note.date)}</time>
          </dd>
          {note.checked ? (
            <>
              <dt>Claims last checked</dt>
              <dd>
                <time dateTime={note.checked}>{formatDate(note.checked)}</time>
              </dd>
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
