import { KIND_LABEL, getNotes } from "@/lib/notes";

export const dynamic = "force-static";

const BASE = "https://clickai.dev";

function escape(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** RFC 822, which is what RSS wants and what Date.toUTCString already gives. */
function rfc822(iso: string): string {
  return new Date(`${iso}T12:00:00Z`).toUTCString();
}

/**
 * One feed for everything in /notes.
 *
 * One rather than two: a second feed on a site this size means one of them
 * going quiet and advertising the fact. A Correction is always a new item and
 * never an edit to an existing one, or a subscriber never sees the retraction.
 */
export function GET() {
  const notes = getNotes();
  const newest = notes[0]?.date;

  const items = notes
    .map((note) =>
      [
        "    <item>",
        `      <title>${escape(`${KIND_LABEL[note.kind]}: ${note.title}`)}</title>`,
        `      <link>${BASE}/notes/${note.slug}</link>`,
        `      <guid isPermaLink="true">${BASE}/notes/${note.slug}</guid>`,
        `      <description>${escape(note.standfirst)}</description>`,
        `      <category>${KIND_LABEL[note.kind]}</category>`,
        `      <pubDate>${rfc822(note.date)}</pubDate>`,
        "    </item>",
      ].join("\n"),
    )
    .join("\n");

  const xml = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
    "  <channel>",
    "    <title>Click AI — field notes</title>",
    `    <link>${BASE}/notes</link>`,
    "    <description>Surveys, corrections and catalog releases. Published when there is something worth checking, not on a schedule.</description>",
    "    <language>en</language>",
    `    <atom:link href="${BASE}/rss.xml" rel="self" type="application/rss+xml"/>`,
    ...(newest ? [`    <lastBuildDate>${rfc822(newest)}</lastBuildDate>`] : []),
    items,
    "  </channel>",
    "</rss>",
    "",
  ].join("\n");

  return new Response(xml, {
    headers: { "content-type": "application/rss+xml; charset=utf-8" },
  });
}
