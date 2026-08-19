import Link from "next/link";
import { human } from "@/lib/human";
import { invocationLabel, type Region } from "@/lib/catalog";

export default function Regions({ regions }: { regions: Region[] }) {
  return (
    <div className="shell regions" id="catalog">
      {regions.map((region) => (
        <section className="region" key={region.id} id={region.id}>
          <div className="region__head">
            <h2 className="region__name">{region.name}</h2>
            <p className="region__blurb">{region.blurb}</p>
            <span className="region__count">
              {region.entries.length} skill{region.entries.length === 1 ? "" : "s"}
            </span>
          </div>

          <ul className="entries">
            {region.entries.map((skill) => (
              <li className="entry" key={skill.slug}>
                <Link className="entry__link" href={`/skills/${skill.slug}`}>
                  <span className="entry__name">{skill.name}</span>
                  <span className="entry__side">
                    <span className="entry__ships">{skill.shipsAs}</span>
                    <span className="entry__invoke">{invocationLabel(skill.invokedBy)}</span>
                  </span>
                  <p className="entry__what">{human(skill.slug).card}</p>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
