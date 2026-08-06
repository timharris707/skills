import type { Metadata } from "next";
import Link from "next/link";
import { KIND_BLURB, KIND_LABEL, formatDate, getNotes, type NoteKind } from "@/lib/notes";

export const metadata: Metadata = {
  title: "Notes",
  description:
    "Field notes on agentic coding: surveys of what a term actually means, corrections when something here turns out wrong, and the reasoning behind catalog changes.",
  alternates: { canonical: "/notes" },
};

const KINDS: NoteKind[] = ["survey", "correction", "release"];

export default function Notes() {
  const notes = getNotes();

  return (
    <>
      <div className="shell" style={{ paddingBlock: "clamp(2.5rem, 6vw, 4rem) 0" }}>
        <p className="eyebrow">Notes</p>
        <h1 style={{ maxWidth: "16ch" }}>Field notes, not a feed.</h1>
        <p className="lede">
          Published when there is something worth checking, not on a schedule. Every claim with a
          date on it gets re-verified, and when one turns out wrong it gets its own entry rather
          than a quiet edit.
        </p>

        <dl className="bands">
          {KINDS.map((kind) => (
            <div key={kind}>
              <dt className={`kind kind--${kind}`}>{KIND_LABEL[kind]}</dt>
              <dd>{KIND_BLURB[kind]}</dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="shell regions">
        <section className="region">
          <div className="region__head">
            <h2 className="region__name">Filed</h2>
            <p className="region__blurb">Newest first.</p>
            <span className="region__count">
              {notes.length} note{notes.length === 1 ? "" : "s"}
            </span>
          </div>

          <ul className="entries">
            {notes.map((note) => (
              <li className="entry" key={note.slug}>
                <Link className="entry__link" href={`/notes/${note.slug}`}>
                  <span className="entry__name">{note.title}</span>
                  <span className={`kind kind--${note.kind}`}>{KIND_LABEL[note.kind]}</span>
                  <p className="entry__what">{note.standfirst}</p>
                  <span className="entry__meta">
                    {formatDate(note.date)} · {note.minutes} min
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </>
  );
}
