import type { Metadata } from "next";
import { openGraph } from "@/lib/meta";
import Link from "next/link";
import { BANDS, ENTRIES, assertLegendSound, byGroup, type Band } from "@/lib/legend";
import { getSkills } from "@/lib/skills";
import {
  DEFINED_TERM_SET,
  definedTermNode,
  graph,
  jsonLdProps,
  PERSON,
} from "@/lib/schema";

export const metadata: Metadata = {
  title: "Legend",
  description:
    "A glossary of agentic coding: context rot, task graphs, verification gates, oracles, and which terms are a rebrand. Each entry says how solid the claim is.",
  alternates: { canonical: "/legend" },
  openGraph: openGraph("/legend"),
};

const BAND_ORDER: Band[] = ["established", "emerging", "contested", "thin"];

export default function Legend() {
  // Fails `next build` on a dangling see-also or a skill that is not in the
  // catalog. A reference work whose links rot is worse than no reference work.
  assertLegendSound(getSkills().map((s) => s.slug));

  const groups = byGroup();

  return (
    <>
      {/* The whole set in one graph: an index page is the natural place to
          declare every term, so a crawler gets the vocabulary in one fetch. */}
      <script
        {...jsonLdProps(
          graph(PERSON, {
            ...DEFINED_TERM_SET,
            hasDefinedTerm: ENTRIES.map(definedTermNode),
          }),
        )}
      />
      <div className="shell" style={{ paddingBlock: "clamp(2.5rem, 6vw, 4rem) 0" }}>
        <p className="eyebrow">Legend</p>
        <h1 style={{ maxWidth: "17ch" }}>The words, and how much they are worth.</h1>
        <p className="lede">
          {ENTRIES.length} terms from agentic coding, defined the way a working engineer would
          accept. Where a term is mostly a rebrand, the entry says so — and says which claim it
          is grading.
        </p>

        <dl className="bands">
          {BAND_ORDER.map((band) => (
            <div key={band}>
              <dt className={`band band--${band}`}>{band}</dt>
              <dd>{BANDS[band]}</dd>
            </div>
          ))}
        </dl>
      </div>

      <div className="shell regions">
        {groups.map(({ group, entries }) => (
          <section className="region" key={group.name} id={group.name.toLowerCase().replace(/\W+/g, "-")}>
            <div className="region__head">
              <h2 className="region__name">{group.name}</h2>
              <p className="region__blurb">{group.standfirst}</p>
              <span className="region__count">
                {entries.length} term{entries.length === 1 ? "" : "s"}
              </span>
            </div>

            <ul className="entries">
              {entries.map((entry) => (
                <li className="entry" key={entry.slug}>
                  <Link className="entry__link" href={`/legend/${entry.slug}`}>
                    <span className="entry__name">{entry.term}</span>
                    <span className={`band band--${entry.band}`}>{entry.band}</span>
                    <p className="entry__what">{entry.gloss}</p>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </>
  );
}
