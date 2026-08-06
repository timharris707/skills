import type { Metadata } from "next";
import Terminal from "@/components/Terminal";
import { getCodexPlugin, getPlugins, getSkills } from "@/lib/skills";

export const metadata: Metadata = {
  title: "Install",
  description: "Add the marketplace once, then install whichever plugins you want.",
  alternates: { canonical: "/install" },
};

export default function Install() {
  const plugins = getPlugins();
  const skills = getSkills();
  const codex = getCodexPlugin();

  return (
    <div className="shell" style={{ paddingBlock: "clamp(2.5rem, 6vw, 4rem) 4rem", maxWidth: "860px" }}>
      <p className="eyebrow">Install</p>
      <h1 style={{ maxWidth: "18ch" }}>Add the marketplace once.</h1>
      <p className="lede">
        Then install whichever plugins you want. Nothing here is locked to one runtime — every
        skill is a <code>SKILL.md</code> any agent can read.
      </p>

      <div className="prose" style={{ maxWidth: "none" }}>
        <h2>Claude Code</h2>
        <Terminal
          lines={[
            { command: "/plugin marketplace add timharris707/skills" },
            ...plugins.map((plugin) => ({
              command: `/plugin install ${plugin.name}@skills`,
              comment: `${plugin.skills.length} skill${plugin.skills.length === 1 ? "" : "s"}`,
            })),
          ]}
        />

        <h2>Codex</h2>
        <p>
          The same {skills.length} skills ship as a native Codex plugin. Codex allows one plugin per
          repository root, so the whole catalog arrives as a single plugin instead of being split
          across several.
        </p>
        <Terminal
          lines={[
            { command: "codex plugin marketplace add timharris707/skills" },
            {
              command: `codex plugin add ${codex.name}@${codex.marketplace}`,
              comment: `${codex.skills} skills`,
            },
          ]}
        />
        <p>
          Every skill carries an adapter at <code>agents/openai.yaml</code> giving Codex the display
          name and one-line description it shows in its picker. CI enforces that both runtimes ship
          the same set, so a skill can never exist on one and silently not on the other.
        </p>

        <h2>Any other runtime</h2>
        <p>
          Clone the repository and point your agent at the skill directories. Symlinks track
          updates on <code>git pull</code>; copies pin what you have.
        </p>
        {/* Skills live in buckets, so glob rather than naming each one — the
            list would go stale the moment a skill moves between buckets. */}
        <pre>
          <code>{`git clone https://github.com/timharris707/skills.git agent-skills
for d in agent-skills/skills/*/*/; do
  [ -f "$d/SKILL.md" ] || continue
  ln -s "$(pwd)/$d" ~/.claude/skills/"$(basename "$d")"
done`}</code>
        </pre>

        <h2>Reading it as an agent</h2>
        <p>
          Every page on this site has a Markdown twin: append <code>.md</code> to any skill URL, or
          start from <a href="/llms.txt">/llms.txt</a> for the whole catalog in one file.
        </p>
      </div>
    </div>
  );
}
