import { BANDS, ENTRIES, getEntry } from "@/lib/legend";

export const dynamic = "force-static";

export function generateStaticParams() {
  return ENTRIES.map((entry) => ({ term: entry.slug }));
}

/** One legend entry as markdown, behind `/legend/<term>.md`. */
export async function GET(_request: Request, context: { params: Promise<{ term: string }> }) {
  const { term } = await context.params;
  const entry = getEntry(term);
  if (!entry) return new Response("Not found\n", { status: 404 });

  const lines = [
    `# ${entry.term}`,
    "",
    `Band: ${entry.band} — ${entry.bandClaim ?? BANDS[entry.band]}`,
    `Group: ${entry.group}`,
    ...(entry.skill ? [`Implemented by: https://clickai.dev/skills/${entry.skill}`] : []),
    "",
    entry.definition,
    "",
  ];

  if (entry.seeAlso?.length) {
    lines.push(
      "## See also",
      "",
      ...entry.seeAlso.map((s) => {
        const other = getEntry(s);
        return `- [${other?.term ?? s}](https://clickai.dev/legend/${s})`;
      }),
      "",
    );
  }

  lines.push("---", "", "Full legend: https://clickai.dev/legend.md", "");

  return new Response(lines.join("\n"), {
    headers: { "content-type": "text/markdown; charset=utf-8" },
  });
}
