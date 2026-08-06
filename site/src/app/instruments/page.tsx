import type { Metadata } from "next";
import Link from "next/link";
import { BENCHES, CHECKED, CLOSING_THE_LOOP, type Instrument } from "@/lib/instruments";
import { formatDate } from "@/lib/notes";

export const metadata: Metadata = {
  title: "Instruments",
  description:
    "The tools these skills are run with — Fallow, CodeGraph, CodeRabbit, CLIProxyAPI and ModelDeck — and the point at which each one stops. Nothing sponsored, no affiliate links.",
  alternates: { canonical: "/instruments" },
};

function Card({ instrument }: { instrument: Instrument }) {
  return (
    <li className="build">
      <div className="build__head">
        <h3 className="build__name">{instrument.name}</h3>
        <span className="build__status">{instrument.status}</span>
      </div>
      <p className="build__what">{instrument.blurb}</p>

      {/* Its own element, not a clause at the end of the blurb. The caveat is
          the reason to read the page. */}
      <p className="instrument__stops">
        <span>Stops at</span>
        {instrument.stopsAt}
      </p>

      {instrument.url || instrument.repo ? (
        <p className="build__links">
          {instrument.url ? (
            <a className="build__link" href={instrument.url} rel="noopener">
              {instrument.url.replace(/^https:\/\//, "")} <span aria-hidden="true">↗</span>
            </a>
          ) : null}
          {instrument.repo ? (
            <a className="build__link" href={instrument.repo} rel="noopener">
              source <span aria-hidden="true">↗</span>
            </a>
          ) : null}
        </p>
      ) : null}
    </li>
  );
}

export default function Instruments() {
  return (
    <>
      <div className="shell" style={{ paddingBlock: "clamp(2.5rem, 6vw, 4rem) 0" }}>
        <p className="eyebrow">Instruments</p>
        <h1 style={{ maxWidth: "18ch" }}>What the work is run with.</h1>
        <p className="lede">
          A surveyor's instruments are bought, not made. Four here I did not write and one I
          did, each with the point at which it stops. Nothing on this page is a skill — these
          are the things the skills are run with.
        </p>
        <p className="instrument__disclosure">
          Nobody paid for a place on this page, there are no affiliate links, and no vendor saw
          it before it published. Claims checked {formatDate(CHECKED)}.
        </p>
      </div>

      <div className="shell regions">
        {BENCHES.map((bench) => (
          <section className="region" key={bench.id} id={bench.id}>
            <div className="region__head">
              <h2 className="region__name">{bench.name}</h2>
              <p className="region__blurb">{bench.blurb}</p>
              <span className="region__count">
                {bench.instruments.length} instrument{bench.instruments.length === 1 ? "" : "s"}
              </span>
            </div>
            <ul className="entries">
              {bench.instruments.map((instrument) => (
                <Card instrument={instrument} key={instrument.name} />
              ))}
            </ul>
          </section>
        ))}
      </div>

      <div className="shell maker maker--brief">
        <div className="maker__head">
          <p className="eyebrow">Closing the loop</p>
          <h2 className="maker__name">{CLOSING_THE_LOOP.title}</h2>
        </div>
        <div className="maker__body">
          {CLOSING_THE_LOOP.body.map((para) => (
            <p key={para.slice(0, 24)}>{para}</p>
          ))}
          <p className="maker__links">
            <Link href="/work">The things I did build →</Link>
          </p>
        </div>
      </div>
    </>
  );
}
