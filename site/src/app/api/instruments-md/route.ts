import { BENCHES, CHECKED, CLOSING_THE_LOOP } from "@/lib/instruments";

export const dynamic = "force-static";

/** The instruments page as markdown, behind `/instruments.md`. */
export function GET() {
  const lines = [
    "# Instruments — what the work is run with",
    "",
    "> A surveyor's instruments are bought, not made. Nothing here is a skill.",
    "> Nobody paid for a place on this page and there are no affiliate links.",
    `> Claims checked ${CHECKED}. Source: https://clickai.dev/instruments`,
    "",
  ];

  for (const bench of BENCHES) {
    lines.push(`## ${bench.name}`, "", bench.blurb, "");
    for (const it of bench.instruments) {
      lines.push(`### ${it.name}${it.mine ? " (mine)" : ""}`, "", `Status: ${it.status}`);
      if (it.url) lines.push(`Site: ${it.url}`);
      if (it.repo) lines.push(`Source: ${it.repo}`);
      lines.push("", it.blurb, "", `**Stops at:** ${it.stopsAt}`, "");
    }
  }

  lines.push(
    `## ${CLOSING_THE_LOOP.title}`,
    "",
    ...CLOSING_THE_LOOP.body.flatMap((p) => [p, ""]),
  );

  return new Response(lines.join("\n"), {
    headers: { "content-type": "text/markdown; charset=utf-8" },
  });
}
