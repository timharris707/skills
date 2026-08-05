import type { Metadata } from "next";
import Terminal from "@/components/Terminal";
import { getPlugins, getSkills } from "@/lib/skills";

export const metadata: Metadata = {
  title: "Install",
  description: "Add the marketplace once, then install whichever plugins you want.",
  alternates: { canonical: "/install" },
};

export default function Install() {
  const plugins = getPlugins();
  const skills = getSkills();

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

        <h2>Any other runtime</h2>
        <p>
          Clone the repository and point your agent at the skill directories. Symlinks track
          updates on <code>git pull</code>; copies pin what you have.
        </p>
        <pre>
          <code>{`git clone https://github.com/timharris707/skills.git agent-skills
for s in ${skills.map((s) => s.slug).join(" ")}; do
  ln -s "$(pwd)/agent-skills/skills/$s" ~/.claude/skills/$s
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
