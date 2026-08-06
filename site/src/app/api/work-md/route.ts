import { BUILD_COUNT, MAKER_LONG, PRIVATE_COUNT, PUBLIC_COUNT, WORK } from "@/lib/work";

export const dynamic = "force-static";

/**
 * The Markdown twin behind `/work.md` (see the rewrite in next.config.ts).
 * Every other page on this site has one; the page where a reader is judging
 * whether the work is real is the last place to drop that promise.
 */
export function GET() {
  const lines = [
    "# Work — Tim Harris",
    "",
    `> ${BUILD_COUNT} builds, one method. ${PUBLIC_COUNT} public, ${PRIVATE_COUNT} private.`,
    "> Product and direction are mine; agents do the implementation, and I review it.",
    "",
  ];

  for (const waters of WORK) {
    lines.push(`## ${waters.name}`, "", waters.blurb, "");
    if (waters.note) lines.push(waters.note, "");
    for (const build of waters.builds) {
      lines.push(`### ${build.name}`, "", `Status: ${build.status}`, "");
      if (build.site && !build.site.startsWith("/")) lines.push(`Site: ${build.site}`);
      if (build.repo) lines.push(`Source: ${build.repo}`);
      if (build.site || build.repo) lines.push("");
      lines.push(build.blurb, "");
    }
  }

  lines.push("## The maker", "", ...MAKER_LONG.flatMap((p) => [p, ""]));
  lines.push("https://github.com/timharris707", "https://insight.tm", "");

  return new Response(lines.join("\n"), {
    headers: { "content-type": "text/markdown; charset=utf-8" },
  });
}
