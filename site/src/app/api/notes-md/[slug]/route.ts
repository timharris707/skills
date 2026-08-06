import { KIND_LABEL, formatDate, getNote, getNotes } from "@/lib/notes";

export const dynamic = "force-static";

export function generateStaticParams() {
  return getNotes().map((note) => ({ slug: note.slug }));
}

/** A note as the markdown it already is, behind `/notes/<slug>.md`. */
export async function GET(_request: Request, context: { params: Promise<{ slug: string }> }) {
  const { slug } = await context.params;
  const note = getNote(slug);
  if (!note) return new Response("Not found\n", { status: 404 });

  const source = [
    `# ${note.title}`,
    "",
    `${KIND_LABEL[note.kind]} · ${formatDate(note.date)}`,
    ...(note.checked ? [`Claims last checked: ${formatDate(note.checked)}`] : []),
    "",
    `> ${note.standfirst}`,
    "",
    note.body.trim(),
    "",
    "---",
    "",
    `Source: https://clickai.dev/notes/${note.slug}`,
    "All notes: https://clickai.dev/notes",
    "",
  ].join("\n");

  return new Response(source, {
    headers: { "content-type": "text/markdown; charset=utf-8" },
  });
}
