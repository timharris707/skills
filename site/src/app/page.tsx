import Link from "next/link";
import Chart from "@/components/Chart";
import Regions from "@/components/Regions";
import Terminal from "@/components/Terminal";
import Runtimes from "@/components/Runtimes";
import { BEARINGS, PLOT, getCatalog } from "@/lib/catalog";

export default function Home() {
  const { regions, skills } = getCatalog();

  const plotted = skills.map((skill) => ({
    slug: skill.slug,
    region: skill.region.name,
    ...PLOT[skill.slug],
  }));

  return (
    <>
      <div className="shell hero">
        <div>
          <Runtimes lead="Runs natively on" />
          <h1>Stop re-explaining your workflow every session.</h1>
          <p className="lede">
            Each skill is a self-contained playbook — a <code>SKILL.md</code> any agent can read,
            plus the templates and scripts it needs. Install once, then invoke it by name.
          </p>

          <Terminal
            lines={[
              { command: "/plugin marketplace add timharris707/skills" },
              { command: "codex plugin marketplace add timharris707/skills" },
            ]}
          />
          <p className="hero__runtimes">
            The same {skills.length} files on both. Neither is a port — CI fails the build if they
            would ship a different set. <Link href="/install">Install →</Link>
          </p>

          <div className="hero__soundings">
            <div>
              <span className="sounding__figure">{skills.length}</span>
              <span className="sounding__label">skills</span>
            </div>
            <div>
              <span className="sounding__figure">{regions.length}</span>
              <span className="sounding__label">regions</span>
            </div>
            <div>
              <span className="sounding__figure">MIT</span>
              <span className="sounding__label">licence</span>
            </div>
          </div>
        </div>

        <Chart skills={plotted} edges={BEARINGS} />
      </div>

      <Regions regions={regions} />
    </>
  );
}
