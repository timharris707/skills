import type { Metadata, Viewport } from "next";
import { Archivo, Newsreader, JetBrains_Mono } from "next/font/google";
import Link from "next/link";
import Runtimes from "@/components/Runtimes";
import ThemeToggle from "@/components/ThemeToggle";
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
    default: "Click AI — portable skills for AI agents",
    template: "%s — Click AI",
  },
  description:
    "Self-contained playbooks any AI agent can read. Install once, invoke by name: grilling, decision maps, prototypes, research lanes, orchestration, and a multi-model advisory board.",
  openGraph: {
    type: "website",
    siteName: "Click AI",
    url: "https://clickai.dev",
  },
  alternates: { canonical: "/" },
};

/* So the browser's own chrome — address bar, scrollbars — is lit the same way
   as the page it frames. */
export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#edf1f1" },
    { media: "(prefers-color-scheme: dark)", color: "#0a1c22" },
  ],
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
          the other lamp. Unset means the operating system decides, which CSS
          already handles on its own.
        */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`,
          }}
        />

        <header className="masthead">
          <div className="shell masthead__inner">
            <Link href="/" className="wordmark">
              <span className="wordmark__fix" aria-hidden="true" />
              clickai.dev
            </Link>
            {/* Five items, and GitHub is not one of them — it lives in the
                colophon as "source". Six turns a hairline masthead into a
                menu. The nav takes its own row below 620px rather than
                competing with the wordmark for space. */}
            <nav>
              <Link href="/skills">Catalog</Link>
              <Link href="/install">Install</Link>
              <Link href="/legend">Legend</Link>
              <Link href="/notes">Notes</Link>
              <Link href="/work">Work</Link>
            </nav>
            <ThemeToggle />
          </div>
        </header>

        <main>{children}</main>

        <footer className="colophon">
          <div className="shell colophon__inner">
            <div style={{ maxWidth: "42ch" }}>
              <p style={{ margin: "0 0 1.1rem" }}>
                Built and maintained by <Link href="/work">Tim Harris</Link>. Every skill on this
                site is generated from its <code>SKILL.md</code>, so the catalog and the code
                cannot drift.
              </p>
              <Runtimes lead="Runs on" />
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
