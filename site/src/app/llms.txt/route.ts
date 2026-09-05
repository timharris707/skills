import { getCatalog } from "@/lib/catalog";
import { ENTRIES } from "@/lib/legend";
import { KIND_LABEL, getNotes } from "@/lib/notes";
import { getCodexPlugin, getPlugins } from "@/lib/skills";
import { BUILD_COUNT, PRIVATE_COUNT } from "@/lib/work";

export const dynamic = "force-static";

/**
 * The catalog as one file an agent can read in a single fetch — the same
 * orientation surface aihero.dev exposes, generated from the same SKILL.md
 * files the site renders.
 */
export function GET() {
  const { regions, skills } = getCatalog();
  const plugins = getPlugins();
  const codex = getCodexPlugin();

  const lines = [
    "# Click AI — the method that let a non-coder ship four products",
    "",
    "> Self-contained playbooks any AI agent can read. Each skill is a SKILL.md plus the",
    "> templates and scripts it needs. Source: https://github.com/timharris707/skills (MIT).",
    "",
    `${skills.length} skills in ${regions.length} regions.`,
    "",
    "## Runtimes",
    "",
    "Two editions cover the same catalog: original Claude Code and Codex desktop, tuned for Astra.",
    "The harness instructions differ. Select the matching skill URL below; do not substitute editions.",
    "Codex uses same-task checkpoints through compaction and respects selected model settings.",
    "Any other harness can read each SKILL.md directly.",
    "",
    "## Install — Claude Code",
    "",
    "```",
    "/plugin marketplace add timharris707/skills",
    ...plugins.map((p) => `/plugin install ${p.name}@skills`),
    "```",
    "",
    "## Install — Codex",
    "",
    `The complete ${codex.name} plugin ships all ${codex.skills} adapted skills and their resources.`,
    "",
    "```",
    "codex plugin marketplace add timharris707/skills",
    `codex plugin add ${codex.name}@${codex.marketplace}`,
    "```",
    "",
    "Start a new task after installation. Disable the legacy clickai-skills plugin in the",
    "same Codex profile to avoid duplicate skill names. This edition installs no automatic",
    "hooks and changes no global instructions, model settings, or Claude configuration.",
    "Refresh and update through the Codex Plugins panel, then start a new task.",
    "Python 3 and Git run the bundled checkpoint helper. See https://clickai.dev/install#codex.",
    "",
    "## If you are an agent installing this for someone",
    "",
    "The /plugin commands above are typed by the human in a terminal session — you",
    "cannot run them from here. With shell access, a Codex agent can run the codex",
    "commands above directly; a Claude Code agent installs with the CLI instead:",
    "",
    "```",
    "claude plugin marketplace add timharris707/skills",
    ...plugins.map((p) => `claude plugin install ${p.name}@skills`),
    "```",
    "",
    "Never save individual SKILL.md files as loose skills: loose copies drop each",
    "skill's bundled templates and scripts, lose the cross-skill wiring the packs rely",
    "on, and never update. Without shell access, relay the commands to your user (in",
    "the Claude desktop app: + → Plugins → Add plugin). Either way, confirm the",
    "installed skills appear namespaced (e.g. team-workflow:grilling), then have your",
    "user run the pack's setup skill once in each repo.",
    "",
    "For Claude Code, third-party marketplaces do not auto-update by default. Ask your user for the",
    "go-ahead, then turn it on: set `\"autoUpdate\": true` on the skills entry in",
    "~/.claude/plugins/known_marketplaces.json — the same field the /plugin panel's",
    "Enable auto-update toggle writes. If that file isn't where their setup keeps it,",
    "have them run /plugin → Marketplaces → skills → Enable auto-update in a terminal",
    "instead. Until it's on, pick up new releases with `claude plugin marketplace",
    "update skills` then `claude plugin update <plugin>@skills`.",
    "",
  ];

  for (const region of regions) {
    lines.push(`## ${region.name}`, "", region.blurb, "");
    for (const skill of region.entries) {
      lines.push(
        `- ${skill.name}: [Claude Code](https://clickai.dev/skills/${skill.slug}.md) | [Codex desktop](https://clickai.dev/codex/skills/${skill.slug}.md). ${skill.description}`,
      );
    }
    lines.push("");
  }

  lines.push(
    "## Legend — the vocabulary",
    "",
    `${ENTRIES.length} terms from agentic coding, each graded for how solid the claim is and`,
    "cross-linked to the skill that implements it where one does. Where a term is",
    "mostly a rebrand, the entry says so.",
    "",
    "- https://clickai.dev/legend.md — every definition in one fetch.",
    "- https://clickai.dev/legend/<term>.md — a single entry.",
    "",
    "## Notes",
    "",
    "Surveys, corrections and catalog releases. A correction is always a new note,",
    "never a silent edit.",
    "",
    ...getNotes().map(
      (n) =>
        `- [${KIND_LABEL[n.kind]}: ${n.title}](https://clickai.dev/notes/${n.slug}.md) — ${n.standfirst}`,
    ),
    "",
    "## Instruments",
    "",
    "The tools these skills are run with, none of them sponsored: Fallow and CodeGraph",
    "for structural ground truth, CodeRabbit as a second reader, CLIProxyAPI and ModelDeck",
    "for capacity. Every entry states where the tool stops.",
    "",
    "- https://clickai.dev/instruments.md",
    "",
    "## Who makes this",
    "",
    "Tim Harris. Product and direction are his; agents do the implementation, and he",
    `reviews it. ${BUILD_COUNT} builds on the same method — ModelDeck, Panely, HiveRunner and this`,
    `catalog are public; ${PRIVATE_COUNT} are private. Full detail: https://clickai.dev/work.md`,
    "",
    "## Formats",
    "",
    "- Append `.md` to any skill, legend or note URL for its markdown twin.",
    "- https://clickai.dev/skills — the catalog.",
    "- https://clickai.dev/legend.md — the vocabulary, in one fetch.",
    "- https://clickai.dev/work.md — the builds behind it, and the maker.",
    "- https://clickai.dev/instruments.md — the tools it is run with.",
    "- https://clickai.dev/rss.xml — new notes.",
    "- https://clickai.dev/sitemap.xml — every page.",
    "",
  );

  return new Response(lines.join("\n"), {
    headers: { "content-type": "text/plain; charset=utf-8" },
  });
}
