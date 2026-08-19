import { readFile } from "node:fs/promises";
import path from "node:path";
import { ImageResponse } from "next/og";
import { notFound } from "next/navigation";
import { getSkill, getSkills } from "@/lib/skills";
import { human } from "@/lib/human";

/**
 * Per-skill link-preview card, in the survey-chart style of the site-wide
 * /opengraph-image.png: night palette, faint chart grid, the magenta mark,
 * JetBrains Mono headline. Satori renders whatever fonts it is handed, so the
 * TTFs live in src/fonts rather than going through next/font.
 */

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "A skill card from the clickai.dev catalog";

export function generateStaticParams() {
  return getSkills().map((skill) => ({ slug: skill.slug }));
}

// The night palette, verbatim from globals.css — light-dark() second values.
const PAPER = "#0a1c22";
const INK = "#dbe7e9";
const MAGENTA = "#f2559f";

/** One faint gridline colour; the CSS grid is ink at 4%, nudged up because
    PNG previews render darker in timelines than a live page does. */
const GRIDLINE = "rgba(219, 231, 233, 0.05)";
const MUTED = "rgba(219, 231, 233, 0.66)";

/**
 * The tagline is the skill's human card line, whole. The longest card today
 * is 211 chars (five rendered lines, which the layout absorbs); the clamp is
 * a backstop for a future line that outgrows that, cutting on a word.
 */
function clip(text: string, max = 240): string {
  if (text.length <= max) return text;
  return `${text.slice(0, text.lastIndexOf(" ", max))} …`;
}

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const skill = getSkill(slug);
  if (!skill) notFound();

  const fonts = path.join(process.cwd(), "src", "fonts");
  const [regular, bold] = await Promise.all([
    readFile(path.join(fonts, "JetBrainsMono-Regular.ttf")),
    readFile(path.join(fonts, "JetBrainsMono-Bold.ttf")),
  ]);

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          padding: "64px 80px 56px",
          backgroundColor: PAPER,
          backgroundImage: `linear-gradient(to right, ${GRIDLINE} 2px, transparent 2px), linear-gradient(to bottom, ${GRIDLINE} 2px, transparent 2px)`,
          backgroundSize: "84px 84px",
          color: INK,
          fontFamily: "JetBrains Mono",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
          {/* The wordmark's mark — the same four-cell grid as --mark in globals.css. */}
          <svg width="34" height="34" viewBox="0 0 32 32">
            <g fill={MAGENTA}>
              <rect x="2" y="2" width="16" height="16" rx="1.5" opacity="0.32" />
              <rect x="20" y="2" width="10" height="16" rx="1.5" opacity="0.32" />
              <rect x="2" y="20" width="16" height="10" rx="1.5" opacity="0.32" />
              <rect x="20" y="20" width="10" height="10" rx="1.5" />
            </g>
          </svg>
          <div style={{ fontSize: 30, fontWeight: 700 }}>clickai.dev</div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", marginTop: "auto" }}>
          <div style={{ fontSize: 82, fontWeight: 700, lineHeight: 1.1, display: "flex" }}>
            <span>{skill.name}</span>
            <span style={{ color: MAGENTA }}>.</span>
          </div>
          <div
            style={{
              width: 520,
              height: 1,
              backgroundColor: "rgba(219, 231, 233, 0.16)",
              margin: "44px 0",
            }}
          />
          <div style={{ fontSize: 30, lineHeight: 1.55, color: MUTED, maxWidth: 980 }}>
            {clip(human(skill.slug).card)}
          </div>
        </div>

        <div style={{ display: "flex", marginTop: "auto", fontSize: 26, color: MUTED }}>
          clickai.dev/skills/{skill.slug}
        </div>
      </div>
    ),
    {
      ...size,
      fonts: [
        { name: "JetBrains Mono", data: regular, weight: 400 },
        { name: "JetBrains Mono", data: bold, weight: 700 },
      ],
    },
  );
}
