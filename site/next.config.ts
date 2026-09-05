import type { NextConfig } from "next";

const config: NextConfig = {
  // SKILL.md files are read from ../skills at build time (see src/lib/skills.ts),
  // so the tracing root is the repository, not this directory.
  outputFileTracingRoot: `${__dirname}/..`,
  async redirects() {
    return [
      // The catalog lives at /skills; keep the aihero-style /learn path working
      // for anyone who followed it here.
      { source: "/learn", destination: "/skills", permanent: true },
    ];
  },
  async rewrites() {
    return [
      // Markdown twins: /skills/<name>.md serves the raw SKILL.md. A literal
      // `[slug].md` directory is not a param segment, so the suffix is matched
      // here and handed to a normal dynamic route.
      { source: "/codex/skills/:slug.md", destination: "/api/codex-skill-md/:slug" },
      { source: "/skills/:slug.md", destination: "/api/skill-md/:slug" },
      { source: "/work.md", destination: "/api/work-md" },
      { source: "/legend.md", destination: "/api/legend-md" },
      { source: "/legend/:term.md", destination: "/api/legend-md/:term" },
      { source: "/notes/:slug.md", destination: "/api/notes-md/:slug" },
      { source: "/instruments.md", destination: "/api/instruments-md" },
    ];
  },
};

export default config;
