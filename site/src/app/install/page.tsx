import type { Metadata } from "next";
import { openGraph } from "@/lib/meta";
import Terminal from "@/components/Terminal";
import Runtimes, { RuntimeMark } from "@/components/Runtimes";
import { getCodexPlugin, getPlugins } from "@/lib/skills";

export const metadata: Metadata = {
  title: "Install",
  description: "Add the marketplace once, then install whichever plugins you want.",
  alternates: { canonical: "/install" },
  openGraph: openGraph("/install"),
};

export default function Install() {
  const plugins = getPlugins();
  const codex = getCodexPlugin();

  return (
    <div className="shell" style={{ paddingBlock: "clamp(2.5rem, 6vw, 4rem) 4rem", maxWidth: "860px" }}>
      <p className="eyebrow">Install</p>
      <h1 style={{ maxWidth: "18ch" }}>Add the marketplace once.</h1>
      <p className="lede">
        Choose the edition for your app. Both cover the same catalog; each carries
        instructions for its own tools and task lifecycle.
      </p>

      <Runtimes lead="Runs natively on" />

      <div className="prose" style={{ maxWidth: "none" }}>
        <h2 id="claude" className="runtime-head">
          <RuntimeMark id="claude" size={22} />
          Claude Code
        </h2>
        <p>
          Claude Code installs plugins one at a time, so the catalog is split into {plugins.length} —
          take the pack on its own, individual skills, or the full set.
        </p>
        <Terminal
          lines={[
            { command: "/plugin marketplace add timharris707/skills" },
            ...plugins.map((plugin) => ({
              command: `/plugin install ${plugin.name}@skills`,
              comment: `${plugin.skills.length} skill${plugin.skills.length === 1 ? "" : "s"}`,
            })),
          ]}
        />
        <p>
          Third-party marketplaces don&apos;t auto-update by default. Turn it on once —{" "}
          <code>/plugin</code> → Marketplaces → skills → Enable auto-update — or new releases wait
          until you run <code>claude plugin update</code> yourself.
        </p>

        <h2 id="codex" className="runtime-head">
          <RuntimeMark id="codex" size={22} />
          Codex desktop, tuned for Astra
        </h2>
        <p>
          All {codex.skills} skills arrive in <code>{codex.name}</code> v{codex.version}, adapted
          for Codex desktop. Use Astra at medium for everyday work and extra high when
          you want more reasoning. The plugin respects your selection; these are workflow
          recommendations, not benchmark results.
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
          Use a current Codex CLI with plugin support. In the desktop app, open Plugins,
          select the Click AI marketplace, and install <strong>Click AI for Codex</strong>.
          Start a new task to load it, then ask for <code>clickai-codex:setup</code> in your project.
        </p>

        <p>
          Already using <code>clickai-skills</code> in Codex? Disable that legacy plugin
          in the same profile when installing this edition to avoid duplicate skill names.
          Its original package remains available. Claude Code installations keep their
          existing commands and versions.
        </p>
        <p>
          This edition keeps checkpoints in the current task through compaction. It installs
          no automatic hooks and changes no global instructions, model settings, accounts,
          or Claude configuration. Python 3 and Git run its bundled checkpoint helper.
          The individual skills explain any additional tools they need.
        </p>
        <p>
          Teams use the same public plugin. Keep organization rules in each project&apos;s
          <code> AGENTS.md</code>. Workspace admins can import the GitHub marketplace.
          If you use several Codex homes, install the same version in each.
          To update, refresh the marketplace and update the plugin in Codex&apos;s Plugins
          panel, then start a new task.
        </p>
        <p>
          <a href="/codex/skills/orchestrate">Read Codex orchestration →</a>{" · "}
          <a href="https://github.com/timharris707/skills/releases?q=clickai-codex">Versioned downloads →</a>
        </p>

        <h2>Any other runtime</h2>
        <p>
          On Claude Code or Codex, use the plugin commands above — agents installing on
          someone&apos;s behalf run the <code>claude plugin</code> or <code>codex plugin</code> CLI
          from their shell, or relay the commands to their user; never copy skills into place one
          file at a time. For harnesses without plugin support, clone the repository and point your
          agent at the skill directories. Symlinks track updates on <code>git pull</code>; copies
          pin what you have.
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
