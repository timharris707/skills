import Link from "next/link";
import Chart from "@/components/Chart";
import Regions from "@/components/Regions";
import Terminal from "@/components/Terminal";
import Runtimes, { RuntimeMark } from "@/components/Runtimes";
import { BEARINGS, PLOT, getCatalog } from "@/lib/catalog";
import { getCodexPlugin } from "@/lib/skills";
import { MAKER_SHORT } from "@/lib/work";
import { graph, jsonLdProps, PERSON, WEBSITE } from "@/lib/schema";

/**
 * The homepage is a funnel, not a catalog: hook, install, the problems these
 * skills fix, an explicit first week, and only then the full reference. The
 * reader should know what to do next at every scroll position. The chart
 * keeps its production seat in the hero (decider call): it makes the catalog
 * legible at a glance and pulls readers in. The no-jargon-above-the-fold rule
 * binds body prose only; the chart's own labels and captions are exempt.
 */
export default function Home() {
  const { regions, skills } = getCatalog();
  const codex = getCodexPlugin();

  const plotted = skills.map((skill) => ({
    slug: skill.slug,
    region: skill.region.name,
    ...PLOT[skill.slug],
  }));

  return (
    <>
      <script {...jsonLdProps(graph(PERSON, WEBSITE))} />

      <div className="shell hero">
        <div>
          <Runtimes lead="Runs natively on" />
          <h1>Skills For Real Non-Engineers</h1>
          <p className="lede">
            I&apos;ve led dev teams for over twenty years. I never wrote the code. These skills
            give me a lead developer who runs the team, so all I have to bring is the idea.
            Four shipped products so far.
          </p>
          <p className="lede">
            Most of these skills started as someone else&apos;s, chiefly Matt Pocock&apos;s{" "}
            <a href="https://github.com/mattpocock/skills">Skills For Real Engineers</a>. I
            rewrote nearly all of them for someone who won&apos;t read the code, and I made them
            work as one system: one <Link href="/skills/orchestrate">orchestrator</Link> session
            takes the idea, decides what gets grilled, mapped, prototyped, built, and reviewed,
            and runs the rest. That&apos;s what lets a non-engineer ship at production quality.
            I talk to that one session the way I&apos;ve always talked to a dev lead.
          </p>
        </div>

        <Chart skills={plotted} edges={BEARINGS} />
      </div>

      <section className="shell" style={{ maxWidth: "860px", paddingBlock: "2.2rem 0" }}>
        <p className="eyebrow">Thirty seconds to install</p>
        <div className="prose" style={{ maxWidth: "none" }}>
          <h3 className="runtime-head">
            <RuntimeMark id="claude" size={20} />
            Claude Code
          </h3>
          <Terminal
            lines={[
              { command: "/plugin marketplace add timharris707/skills" },
              { command: "/plugin install team-workflow@skills", comment: "the pack, start here" },
            ]}
          />
          <h3 className="runtime-head">
            <RuntimeMark id="codex" size={20} />
            Codex desktop, tuned for Astra
          </h3>
          <Terminal
            lines={[
              { command: "codex plugin marketplace add timharris707/skills" },
              { command: `codex plugin add ${codex.name}@${codex.marketplace}` },
            ]}
          />
          <p>
            That&apos;s the install. Open a session in a real repo and you can ask for any skill
            by name. Both editions cover all {skills.length} skills, with instructions adapted to each app.
            The Codex edition keeps task ownership through compaction and respects your model settings. Standalone skills and other
            runtimes: <Link href="/install">every install option →</Link>
          </p>
          <h3>Start with the seat, not the list</h3>
          <p>
            Install the pack, run <Link href="/skills/setup">setup</Link> once, then open one
            session and say &ldquo;orchestration mode.&rdquo; That session is your lead. It
            reads the map, routes the work to the other skills, and comes back to you only for
            decisions. Setup asks whether you&apos;ll read the code your agents write or lead
            from outside it; answer lead, and every new session in that repo opens in the seat.
            The chart above is what your lead has to work with.
          </p>
        </div>
      </section>

      <section className="shell" style={{ maxWidth: "860px", paddingBlock: "2.8rem 0" }}>
        <p className="eyebrow">What these fix</p>
        <div className="prose">
          <h2 style={{ borderTop: "none", paddingTop: 0, marginTop: 0 }}>
            Stop re-explaining your workflow every session
          </h2>
          <p>
            You finally got a session working the way you work. It knew the plan, the
            standards, the things it must never touch. Then it ended, and this morning&apos;s
            agent knows none of it. Every skill here is a workflow I got tired of re-teaching,
            written down once, so any agent can pick it up by name. Four failures cost me the
            most, and the fix was never a smarter model. It is a written procedure the agent
            cannot skip.
          </p>

          {/* Each failure mode is self-contained on purpose — the four working
              names are proposed, not final, so a wording swap must never touch
              a neighbouring block. */}
          <h3>&ldquo;It built the wrong thing, confidently.&rdquo;</h3>
          <p>
            You described the feature, the agent agreed instantly, and hours later you are
            reviewing a polished implementation of something you never meant. Nobody
            pressure-tested the plan, so the agent filled every gap with a guess, and the cost
            lands at review time, the most expensive place to find out.{" "}
            <Link href="/skills/grilling">grilling</Link> inverts the ritual: the agent
            interviews you, round after round, and it is done when no question on the table is
            still open and the settled decisions are written down. It will not make the calls
            for you. You decide everything; it just refuses to let a question slide by
            unanswered.
          </p>

          <h3>&ldquo;One model&apos;s opinion.&rdquo;</h3>
          <p>
            An architecture, a migration, a contract: a hard call, decided by whichever model
            you happened to ask, in one pass, with nobody pushing back. When that call is
            wrong, you rebuild. <Link href="/skills/advisory-board">advisory-board</Link>{" "}
            convenes Claude, Codex, Gemini, and Grok on the same material, has them answer
            independently and then read each other, and is done when you hold one verdict with
            the dissent preserved and a list of what the board could not verify. The board
            never edits your files, and it is still models arguing with models. The final
            call stays yours.
          </p>

          <h3>&ldquo;The session died and took the state with it.&rdquo;</h3>
          <p>
            Yesterday&apos;s session knew the plan, the constraints, and the half-finished
            thread. Then it hit its limit, and today&apos;s opens blank, so you spend the
            start of every session rebuilding the end of the last one.{" "}
            <Link href="/skills/handoff">handoff</Link> is done when one small file lets a
            fresh session resume mid-stride with nothing re-explained, and{" "}
            <Link href="/skills/domain-memory">domain-memory</Link> keeps the permanent layer:
            what your repo&apos;s words mean, and why its settled decisions went the way they
            did. A handoff is a pointer, not a transcript. It records where things stand and
            where the durable records live, never the whole conversation.
          </p>

          <h3>&ldquo;You&apos;re the bottleneck between five agents.&rdquo;</h3>
          <p>
            Parallel agents sound like leverage until every one of them needs context only you
            hold, and the work moves at the speed of your typing.{" "}
            <Link href="/skills/to-tickets">to-tickets</Link> turns a decided plan into tracker
            items a stranger could pick up cold, blocking edges included, and{" "}
            <Link href="/skills/orchestrate">orchestrate</Link> is done when your session
            plays the lead: it assigns, audits, and merges instead of implementing. Neither will untangle an
            undecided mess: they need a plan already settled and a tracker to put it on.
          </p>
        </div>
      </section>

      <section className="shell" style={{ maxWidth: "860px", paddingBlock: "2.8rem 0" }}>
        <p className="eyebrow">Start here</p>
        <div className="prose">
          <h2 style={{ borderTop: "none", paddingTop: 0, marginTop: 0 }}>Your first week</h2>
          <ol>
            <li>
              <strong>Point the pack at one real repo.</strong> Run the install above, then
              tell a session in that repo to run <Link href="/skills/setup">setup</Link>. It is
              a short interview, once per repo: how you test, where work is tracked, who has
              the final say, and whether you read the code or lead from outside it. It records;
              it never restructures what you already have. You will notice every later skill
              stops asking you those questions.
            </li>
            <li>
              <strong>Grill your next real plan.</strong> Pick something you were going to
              build anyway and run <Link href="/skills/grilling">grilling</Link> on it first.
              It works only as hard as your answers, so bring real attention. You will notice a
              question you cannot answer cleanly — that question was headed for the codebase.
            </li>
            <li>
              <strong>
                Close with <Link href="/skills/handoff">handoff</Link>, then open a fresh
                session.
              </strong>{" "}
              It reads one small file and resumes mid-stride; deep history stays in the records
              that file points to. This is where the catalog earns its keep: the re-explaining
              just stops.
            </li>
            <li>
              <strong>
                When a call is worth real money, convene{" "}
                <Link href="/skills/advisory-board">advisory-board</Link>.
              </strong>{" "}
              Four vendors&apos; frontier models on one question beats one model&apos;s first
              answer. Expect it to take longer than asking once. Deliberation is the point.
            </li>
            <li>
              <strong>
                For the rest, ask <Link href="/skills/router">router</Link>.
              </strong>{" "}
              It names every skill in the pack and when to reach for each. It is a map, not a
              manager — it points, you invoke.
            </li>
          </ol>
        </div>
      </section>

      <section className="shell" style={{ paddingBlock: "3rem 0" }}>
        <p className="eyebrow">The catalog</p>
        <div className="prose">
          <h2 style={{ borderTop: "none", paddingTop: 0, marginTop: 0 }}>
            All {skills.length} skills
          </h2>
          <p>
            The full reference: {skills.length} skills in {regions.length} regions, MIT
            licensed, each one a self-contained <code>SKILL.md</code> any agent can read plus
            the templates and scripts it needs. The chart at the top of the page plots how
            they hand work to each other; the vocabulary it speaks — fixes, bearings, lanes —
            is defined in the <Link href="/legend">legend</Link>.
          </p>
        </div>
      </section>

      <Regions regions={regions} />

      {/* Below the catalog on purpose: the reader meets the argument and the
          artefact first, so this answers "who made this?" instead of opening
          with a boast. */}
      <section className="shell maker maker--brief">
        <div className="maker__head">
          <p className="eyebrow">The maker</p>
          <h2 className="maker__name">Tim Harris</h2>
        </div>
        <div className="maker__body">
          <p className="maker__thesis">I never wrote the code. I lead the team that does.</p>
          <p>{MAKER_SHORT}</p>
          <p className="maker__links">
            <Link href="/work">The rest of the work →</Link>
          </p>
        </div>
      </section>

      {/* The flip toggle ships separately; this line stands alone either way,
          because the Markdown twins it describes already exist. */}
      <section className="shell" style={{ maxWidth: "860px", paddingBlock: "0 4rem" }}>
        <p className="hero__runtimes" style={{ maxWidth: "none" }}>
          This page has a twin written for agents. Append <code>.md</code> to any skill URL, or
          start at <a href="/llms.txt">llms.txt</a>, and you are reading exactly what my agents
          read.
        </p>
      </section>
    </>
  );
}
