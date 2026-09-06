import type { Metadata, Viewport } from "next";
import { Archivo, Newsreader, JetBrains_Mono } from "next/font/google";
import Link from "next/link";
import { FlipProvider, FlipToggle, FlipView } from "@/components/AgentFlip";
import Runtimes from "@/components/Runtimes";
import ThemeToggle from "@/components/ThemeToggle";
import { openGraph } from "@/lib/meta";
import "./globals.css";

const body = Archivo({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-body",
  display: "swap",
});

// Region names are lettered like the water features on a survey chart.
const display = Newsreader({
  subsets: ["latin"],
  weight: ["400"],
  style: ["italic"],
  variable: "--font-display",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "700"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://clickai.dev"),
  title: {
    default: "Click AI — Skills For Real Non-Engineers",
    template: "%s — Click AI",
  },
  description:
    "Workflows written down once, as skills any agent can read. Install once, invoke by name: grilling, decision maps, prototypes, research lanes, orchestration, and a multi-model advisory board.",
  // Pages override this with their own path — see src/lib/meta.ts for why the
  // whole block is repeated rather than just the url.
  openGraph: openGraph("/"),
  alternates: { canonical: "/" },
  // The colophon has said this in prose since the site launched; these say it
  // in the form a crawler reads. Inherited by every route.
  authors: [{ name: "Tim Harris", url: "https://clickai.dev/work" }],
  creator: "Tim Harris",
  publisher: "Tim Harris",
};

/* So the browser's own chrome — address bar, scrollbars — is lit the same way
   as the page it frames. One value, not a media pair: the page itself no longer
   follows the operating system, so chrome that did would disagree with it. The
   pre-paint script and the lamp correct this when night is pinned. */
export const viewport: Viewport = {
  themeColor: "#edf1f1",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    // The script below sets data-theme before React hydrates, so the server
    // markup and the live DOM legitimately disagree on this one element.
    // Suppression is one level deep, which is exactly the scope of the lie.
    <html
      lang="en"
      className={`${body.variable} ${display.variable} ${mono.variable}`}
      suppressHydrationWarning
    >
      <body>
        {/*
          Runs before the first paint. A pinned theme has to be on <html> in
          the opening frame; resolved any later and the page visibly flashes
          the other lamp. Unset means daylight, which CSS already gives for
          free — so this only has work to do when a reader has chosen night,
          and it moves the browser chrome to match in the same frame.
        */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var t=localStorage.getItem("theme");if(t==="light"||t==="dark"){document.documentElement.dataset.theme=t;if(t==="dark"){var m=document.querySelector('meta[name="theme-color"]');if(m)m.setAttribute("content","#0a1c22")}}}catch(e){}`,
          }}
        />

        {/* The human ⇄ agent flip spans two landmarks — its control sits in
            the masthead, its rendering replaces the page — so the provider
            has to stand over both. Everything inside is still server-rendered;
            the provider only passes it through. */}
        <FlipProvider>
          <header className="masthead">
            <div className="shell masthead__inner">
              <Link href="/" className="wordmark">
                <span className="wordmark__fix" aria-hidden="true" />
                clickai.dev
              </Link>
              {/* Six items, and GitHub is not one of them — it lives in the
                  colophon as "source". Home is spelled out because readers do
                  not know the wordmark is a link and the homepage is the
                  pitch (decider, 2026-09-05). The nav takes its own row below
                  620px rather than competing with the wordmark for space. */}
              <nav>
                <Link href="/">Home</Link>
                <Link href="/skills">Catalog</Link>
                <Link href="/install">Install</Link>
                <Link href="/legend">Legend</Link>
                <Link href="/notes">Notes</Link>
                <Link href="/work">Work</Link>
              </nav>
              <FlipToggle />
              <ThemeToggle />
            </div>
          </header>

          <main>
            <FlipView>{children}</FlipView>
          </main>
        </FlipProvider>

        <footer className="colophon">
          <div className="shell colophon__inner">
            <div style={{ maxWidth: "42ch" }}>
              <p style={{ margin: "0 0 1.1rem" }}>
                Built and maintained by <Link href="/work">Tim Harris</Link>. Every skill on this
                site is generated from its <code>SKILL.md</code>, so the catalog and the code
                cannot drift.
              </p>
              <Runtimes lead="Runs on" />
              <p className="colophon__aside">
                <Link href="/instruments">Instruments</Link> — what the work is run with.
              </p>
            </div>
            <div className="colophon__links">
              <a href="https://github.com/timharris707/skills">source</a>
              <a href="https://x.com/TimHarris707">@TimHarris707</a>
              <Link href="/rss.xml">rss</Link>
              <Link href="/llms.txt">llms.txt</Link>
              <a href="https://github.com/timharris707/skills/blob/main/LICENSE.md">MIT</a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
