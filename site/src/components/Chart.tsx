"use client";

import Link from "next/link";
import { useState } from "react";

export type ChartSkill = {
  slug: string;
  x: number;
  y: number;
  region: string;
  anchor?: "start" | "end";
};
export type ChartEdge = { from: string; to: string; note: string };

/**
 * The plotting board: every skill as a position fix, every documented handoff
 * between them as a bearing. Hovering a fix lights the bearings it sits on, so
 * the question a catalog usually leaves to prose — which of these do I need,
 * and in what order — is answerable by pointing at it.
 */
export default function Chart({
  skills,
  edges,
}: {
  skills: ChartSkill[];
  edges: ChartEdge[];
}) {
  const [active, setActive] = useState<string | null>(null);

  const at = new Map(skills.map((s) => [s.slug, s]));
  const lit = edges.filter((e) => e.from === active || e.to === active);
  const connected = new Set(lit.flatMap((e) => [e.from, e.to]));


  return (
    <div className="chart">
      <div className="chart__title">
        <span>Fig. 1 — how they compose</span>
        <span>{skills.length} fixes · {edges.length} bearings</span>
      </div>

      <svg viewBox="0 0 1000 520" role="img" aria-label="Diagram of how the skills hand off to each other. The same information is listed by region below.">
        <g>
          {edges.map((edge) => {
            const a = at.get(edge.from);
            const b = at.get(edge.to);
            if (!a || !b) return null;
            const isLit = active !== null && (edge.from === active || edge.to === active);
            const isDim = active !== null && !isLit;
            const className = `bearing${isLit ? " bearing--lit" : ""}${
              isDim ? " bearing--dimmed" : ""
            }`;

            // Two fixes in the same column need a vertical run — easing them
            // horizontally would send the bearing out and back on itself.
            let d: string;
            if (Math.abs(b.x - a.x) < 40) {
              const from = { x: a.x, y: a.y + (b.y > a.y ? 10 : -10) };
              const to = { x: b.x, y: b.y + (b.y > a.y ? -10 : 10) };
              const bow = 26;
              d = `M ${from.x} ${from.y} C ${from.x + bow} ${from.y}, ${to.x + bow} ${to.y}, ${to.x} ${to.y}`;
            } else {
              // Leave on the right edge, arrive on the left, easing horizontally
              // so the run reads as a plotted course rather than a wire.
              const from = { x: a.x + 10, y: a.y };
              const to = { x: b.x - 10, y: b.y };
              const ease = Math.min(95, Math.max(34, Math.abs(to.x - from.x) * 0.42));
              d = `M ${from.x} ${from.y} C ${from.x + ease} ${from.y}, ${to.x - ease} ${to.y}, ${to.x} ${to.y}`;
            }

            return <path key={`${edge.from}-${edge.to}`} d={d} className={className} />;
          })}
        </g>

        <g>
          {skills.map((skill) => {
            const isActive = skill.slug === active;
            const isLit = isActive || connected.has(skill.slug);
            const isDim = active !== null && !isLit;
            const toEnd = skill.anchor === "end";
            return (
              <Link
                key={skill.slug}
                href={`/skills/${skill.slug}`}
                className={`fix${isLit && active !== null ? " fix--lit" : ""}${isDim ? " fix--dimmed" : ""}`}
                onMouseEnter={() => setActive(skill.slug)}
                onMouseLeave={() => setActive(null)}
                onFocus={() => setActive(skill.slug)}
                onBlur={() => setActive(null)}
              >
                <circle className="fix__ring" cx={skill.x} cy={skill.y} r={8} />
                <circle className="fix__dot" cx={skill.x} cy={skill.y} r={2.8} />
                <text
                  className="fix__label"
                  x={toEnd ? skill.x - 17 : skill.x + 17}
                  y={skill.y}
                  textAnchor={toEnd ? "end" : "start"}
                >
                  {skill.slug}
                </text>
              </Link>
            );
          })}
        </g>
      </svg>

      {/* Fixed height: hovering a fix must not reflow the page around it. */}
      <div className="chart__legend">
        {active === null && <p className="chart__hint">Point at a skill to trace what feeds it and what it feeds.</p>}
        {active !== null && lit.length === 0 && (
          <p className="chart__hint">
            <strong>{active}</strong> stands apart — nothing in the flow hands to it.
          </p>
        )}
        {active !== null && lit.length > 0 && (
          <ul className="bearings">
            {lit.map((edge) => (
              <li key={`${edge.from}-${edge.to}`}>
                <span className="bearings__run">
                  {edge.from} <span aria-hidden="true">→</span> {edge.to}
                </span>
                <span className="bearings__note">{edge.note}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
