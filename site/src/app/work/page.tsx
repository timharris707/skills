import type { Metadata } from "next";
import { openGraph } from "@/lib/meta";
import Link from "next/link";
import {
  BUILD_COUNT,
  LEDGER,
  MAKER_LONG,
  PRIVATE_COUNT,
  PUBLIC_COUNT,
  WORK,
  type Build,
} from "@/lib/work";

export const metadata: Metadata = {
  title: "Work",
  description:
    `${BUILD_COUNT} builds, one method: ModelDeck, Panely, HiveRunner, this catalog, and ${PRIVATE_COUNT} private builds. Made by Tim Harris, who never wrote the code and leads the agent team that does.`,
  alternates: { canonical: "/work" },
  openGraph: openGraph("/work"),
};

/** An internal path stays a Link; anything else leaves the site. */
function Visit({ href, children }: { href: string; children: React.ReactNode }) {
  if (href.startsWith("/")) {
    return (
      <Link className="build__link" href={href}>
        {children}
      </Link>
    );
  }
  return (
    <a className="build__link" href={href} rel="noopener">
      {children} <span aria-hidden="true">↗</span>
    </a>
  );
}

function BuildRow({ build }: { build: Build }) {
  return (
    <li className="build">
      <div className="build__head">
        <h3 className="build__name">{build.name}</h3>
        <span className="build__status">{build.status}</span>
      </div>
      <p className="build__what">{build.blurb}</p>
      {/* Private builds get no links at all — a 404 on a private repository
          discloses its name, and an inert card discloses nothing. */}
      {build.site || build.repo ? (
        <p className="build__links">
          {build.site ? <Visit href={build.site}>{build.site.replace(/^https:\/\//, "")}</Visit> : null}
          {build.repo ? <Visit href={build.repo}>source</Visit> : null}
        </p>
      ) : null}
    </li>
  );
}

/**
 * Human copy on this page is first person. This block is the only third-person
 * text, because it is the one a machine reads — it is what makes the name
 * resolve to a person in search and agent contexts rather than to a product.
 */
const PERSON = {
  "@context": "https://schema.org",
  "@type": "Person",
  name: "Tim Harris",
  url: "https://clickai.dev/work",
  description:
    "Never wrote the code; leads the agent team that does. Maker of ModelDeck, Panely, HiveRunner, and the Click AI skills catalog.",
  sameAs: [
    "https://github.com/timharris707",
    "https://x.com/TimHarris707",
    "https://modeldeck.ai",
    "https://panely.ai",
    "https://hiverunner.ai",
  ],
};

export default function Work() {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(PERSON) }}
      />

      <div className="shell" style={{ paddingBlock: "clamp(2.5rem, 6vw, 4rem) 0" }}>
        <p className="eyebrow">Work</p>
        <h1 style={{ maxWidth: "15ch" }}>{BUILD_COUNT} builds. One method.</h1>
        <p className="lede">
          {PUBLIC_COUNT} you can install today. {PRIVATE_COUNT} you cannot see. All of them
          shipped the same way — I make the product calls and hold the standard, agents do the
          typing.
        </p>
        <p className="instrument__disclosure">
          <Link href="/instruments">What the work is run with →</Link>
        </p>
      </div>

      <div className="shell regions">
        {WORK.map((waters) => (
          <section className="region" key={waters.id} id={waters.id}>
            <div className="region__head">
              <h2 className="region__name">{waters.name}</h2>
              <p className="region__blurb">{waters.blurb}</p>
              {waters.note ? <p className="region__note">{waters.note}</p> : null}
              <span className="region__count">
                {waters.builds.length} build{waters.builds.length === 1 ? "" : "s"}
              </span>
            </div>

            <ul className="entries">
              {waters.builds.map((build) => (
                <BuildRow build={build} key={build.name} />
              ))}
            </ul>
          </section>
        ))}
      </div>

      {/* The figures run before the biography. They are checkable against a
          public profile, which the biography is not, so they carry more. */}
      <div className="shell maker">
        <div className="maker__head">
          <p className="eyebrow">{LEDGER.eyebrow}</p>
          <h2 className="maker__name">Six months.</h2>
        </div>
        <div className="maker__body">
          {LEDGER.lines.map((line) => (
            <p key={line.slice(0, 24)}>{line}</p>
          ))}
        </div>
      </div>

      <div className="shell maker">
        <div className="maker__head">
          <p className="eyebrow">The maker</p>
          <h2 className="maker__name">Tim Harris</h2>
        </div>
        <div className="maker__body">
          {MAKER_LONG.map((para) => (
            <p key={para.slice(0, 24)}>{para}</p>
          ))}
          <p className="maker__links">
            <a href="https://github.com/timharris707" rel="noopener">
              github.com/timharris707
            </a>
            <a href="https://x.com/TimHarris707" rel="noopener">
              @TimHarris707
            </a>
            <a href="https://insight.tm" rel="noopener">
              insight.tm
            </a>
          </p>
        </div>
      </div>
    </>
  );
}
