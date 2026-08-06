import fs from "node:fs";
import path from "node:path";

/**
 * Field notes — deliberately not a blog.
 *
 * A dated opinion feed decays visibly and competes with a Twitter account for
 * the same material. Three kinds instead, each with a reason to exist:
 *
 *   survey      — a full investigation of something, with sources
 *   correction  — a claim on this site that turned out to be wrong
 *   release     — a dated catalog change and the reasoning behind it
 *
 * `correction` is the one worth defending. A site whose pitch is that it tells
 * the truth about buzzwords needs somewhere to publish having been wrong, and
 * a correction is always a NEW note, never a silent edit to the old one — or
 * nobody subscribed to the feed ever sees the retraction.
 *
 * A survey carries `checked`, separate from `date`. Its credibility is the
 * freshness of its claims, and a reader cannot otherwise tell whether "no
 * benchmark exists" was verified last week or last year.
 */

const NOTES_DIR = path.join(process.cwd(), "content", "notes");

export type NoteKind = "survey" | "correction" | "release";

export const KIND_LABEL: Record<NoteKind, string> = {
  survey: "Survey",
  correction: "Correction",
  release: "Release",
};

export const KIND_BLURB: Record<NoteKind, string> = {
  survey: "A full investigation, with its sources and its gaps.",
  correction: "A claim on this site that turned out to be wrong.",
  release: "A change to the catalog, and why it was made.",
};

export type Note = {
  slug: string;
  title: string;
  kind: NoteKind;
  /** Publication date, ISO. */
  date: string;
  /** When the claims were last re-verified. Surveys only. */
  checked?: string;
  standfirst: string;
  body: string;
  /** Rough reading cost, so a reader can decide before committing. */
  minutes: number;
};

function parseFrontmatter(raw: string): { data: Record<string, string>; body: string } {
  if (!raw.startsWith("---")) return { data: {}, body: raw };
  const end = raw.indexOf("\n---", 3);
  if (end === -1) return { data: {}, body: raw };

  const data: Record<string, string> = {};
  for (const line of raw.slice(3, end).split("\n")) {
    const match = line.match(/^([A-Za-z][\w-]*):\s*(.*)$/);
    if (match) data[match[1]] = match[2].trim();
  }
  return { data, body: raw.slice(end + 4).replace(/^\r?\n/, "") };
}

let cache: Note[] | null = null;

export function getNotes(): Note[] {
  if (cache) return cache;
  if (!fs.existsSync(NOTES_DIR)) return (cache = []);

  const notes: Note[] = [];
  for (const file of fs.readdirSync(NOTES_DIR)) {
    if (!file.endsWith(".md")) continue;
    const { data, body } = parseFrontmatter(fs.readFileSync(path.join(NOTES_DIR, file), "utf8"));
    const kind = (data.kind ?? "survey") as NoteKind;
    if (!(kind in KIND_LABEL)) {
      throw new Error(`content/notes/${file}: unknown kind "${kind}"`);
    }
    notes.push({
      slug: file.replace(/\.md$/, ""),
      title: data.title ?? file,
      kind,
      date: data.date ?? "",
      checked: data.checked || undefined,
      standfirst: data.standfirst ?? "",
      body,
      // 200 wpm, rounded up. Close enough to set an expectation, which is all
      // it is for.
      minutes: Math.max(1, Math.round(body.split(/\s+/).length / 200)),
    });
  }

  return (cache = notes.sort((a, b) => b.date.localeCompare(a.date)));
}

export function getNote(slug: string): Note | undefined {
  return getNotes().find((n) => n.slug === slug);
}

/** Long-form dates, written the way the rest of the site writes them. */
export function formatDate(iso: string): string {
  if (!iso) return "";
  const [y, m, d] = iso.split("-").map(Number);
  const months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];
  return `${d} ${months[m - 1]} ${y}`;
}
