import { BANDS, ENTRIES, byGroup } from "@/lib/legend";

export const dynamic = "force-static";

/**
 * The whole legend in one fetch, behind `/legend.md`.
 *
 * The web page is built to be scanned — a term, a band, one line. This is the
 * opposite surface and wants the opposite shape: every definition in full,
 * because an agent loading it is paying for one request and wants everything.
 */
export function GET() {
  const lines = [
    "# Legend — the words, and how much they are worth",
    "",
    `> ${ENTRIES.length} terms from agentic coding. Where a term is mostly a rebrand, the entry says so.`,
    "> Source: https://clickai.dev/legend",
    "",
    "## How to read the bands",
    "",
    ...Object.entries(BANDS).map(([band, meaning]) => `- **${band}** — ${meaning}`),
    "",
    "A band grades a *claim*, not a word. Where the claim being graded is narrower",
    "than the term, the entry states it.",
    "",
  ];

  for (const { group, entries } of byGroup()) {
    lines.push(`## ${group.name}`, "", group.standfirst, "");
    for (const entry of entries) {
      lines.push(`### ${entry.term}`, "", `Band: ${entry.band}`);
      if (entry.bandClaim) lines.push(`Grading: ${entry.bandClaim}`);
      if (entry.skill) lines.push(`Implemented by: https://clickai.dev/skills/${entry.skill}`);
      lines.push("", entry.definition, "");
      if (entry.seeAlso?.length) {
        lines.push(
          `See also: ${entry.seeAlso.map((s) => `https://clickai.dev/legend/${s}`).join(", ")}`,
          "",
        );
      }
    }
  }

  return new Response(lines.join("\n"), {
    headers: { "content-type": "text/markdown; charset=utf-8" },
  });
}
