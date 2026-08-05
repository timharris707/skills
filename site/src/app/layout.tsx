import type { Metadata } from "next";
import { Archivo, Newsreader, JetBrains_Mono } from "next/font/google";
import Link from "next/link";
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

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${body.variable} ${display.variable} ${mono.variable}`}>
      <body>
        <header className="masthead">
          <div className="shell masthead__inner">
            <Link href="/" className="wordmark">
              <span className="wordmark__fix" aria-hidden="true" />
              clickai.dev
            </Link>
            <nav>
              <Link href="/skills">Catalog</Link>
              <Link href="/install">Install</Link>
              <a href="https://github.com/timharris707/skills">GitHub</a>
            </nav>
          </div>
        </header>

        <main>{children}</main>

        <footer className="colophon">
          <div className="shell colophon__inner">
            <p style={{ margin: 0, maxWidth: "42ch" }}>
              Built and maintained by{" "}
              <a href="https://github.com/timharris707">Tim Harris</a>. Every skill on this site is
              generated from its <code>SKILL.md</code>, so the catalog and the code cannot drift.
            </p>
            <div className="colophon__links">
              <a href="https://github.com/timharris707/skills">source</a>
              <Link href="/llms.txt">llms.txt</Link>
              <a href="https://github.com/timharris707/skills/blob/main/LICENSE.md">MIT</a>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
