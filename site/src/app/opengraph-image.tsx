import { readFile } from "node:fs/promises";
import path from "node:path";
import { ImageResponse } from "next/og";

/**
 * The site-wide link-preview card, rendered from the same copy of record as
 * the hero (decision 0005) so the picture can never drift from the headline
 * again; the previous static PNG still showed a retired line after the hero
 * changed. Same survey-chart style as the per-skill cards in skills/[slug].
 */

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "Skills For Real Non-Engineers — clickai.dev";

const PAPER = "#0a1c22";
const INK = "#dbe7e9";
const MAGENTA = "#f2559f";
const GRIDLINE = "rgba(219, 231, 233, 0.05)";
const MUTED = "rgba(219, 231, 233, 0.66)";

export default async function Image() {
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
          <div style={{ fontSize: 76, fontWeight: 700, lineHeight: 1.1, display: "flex", flexDirection: "column" }}>
            <span>Skills For Real</span>
            <span>
              Non-Engineers<span style={{ color: MAGENTA }}>.</span>
            </span>
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
            I never wrote the code. These skills give me a lead developer who runs the team, so all I
            have to bring is the idea.
          </div>
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
