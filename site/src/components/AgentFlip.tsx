"use client";

import { usePathname } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

/**
 * The human ⇄ agent flip.
 *
 * Every page here that an agent might consume has a Markdown twin — the raw
 * bytes behind `/skills/<name>.md`, `/legend.md`, and so on (see the rewrites
 * in next.config.ts). The flip shows that twin in place of the human page:
 * same URL bar, same content, the other audience's rendering. The agent view
 * is fetched from the twin route itself — the exact URL an agent would hit —
 * never from a second copy that could drift.
 *
 * Three pieces share one context: the provider (owns which side is showing),
 * the toggle (lives in the masthead, hidden on pages with no twin), and the
 * view (wraps <main>'s children and swaps them for the fetched Markdown).
 * The state is mirrored into the URL as `?view=agent` so a flipped page is
 * shareable, and read back out on load so a shared link opens flipped.
 */

/** The twin route for a pathname, or null when the page has none. */
export function twinFor(pathname: string): string | null {
  if (pathname === "/") return "/llms.txt";
  if (pathname === "/work") return "/work.md";
  if (pathname === "/legend") return "/legend.md";
  if (pathname === "/instruments") return "/instruments.md";
  // One segment deep only — the twins are per-entry, not per-anything-deeper.
  if (/^\/(skills|legend|notes)\/[^/]+$/.test(pathname)) return `${pathname}.md`;
  return null;
}

type View = "human" | "agent";

const FlipContext = createContext<{ view: View; twin: string | null; toggle: () => void }>({
  view: "human",
  twin: null,
  toggle: () => {},
});

export function FlipProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const twin = twinFor(pathname);
  const [view, setView] = useState<View>("human");

  // The URL is the source of truth. Pages are statically prerendered, so the
  // query string cannot be read on the server; the first paint is always the
  // human page and a `?view=agent` link flips as soon as this runs. Keyed on
  // pathname so client-side navigation — where the fresh URL carries no
  // `?view` — lands on the human side again.
  useEffect(() => {
    const read = () =>
      setView(new URLSearchParams(window.location.search).get("view") === "agent"
        ? "agent"
        : "human");
    read();
    // Back/forward moves through flips the same way it moves through pages.
    window.addEventListener("popstate", read);
    return () => window.removeEventListener("popstate", read);
  }, [pathname]);

  const toggle = useCallback(() => {
    // The URL work stays outside the state updater: Strict Mode may invoke
    // updaters twice in development, which would push duplicate history
    // entries per click.
    const next = view === "human" ? "agent" : "human";
    const url = new URL(window.location.href);
    if (next === "agent") url.searchParams.set("view", "agent");
    else url.searchParams.delete("view");
    // Native pushState, not a router navigation: the flip is client-side
    // and instant, and there is nothing new to ask the server for.
    window.history.pushState(null, "", url);
    setView(next);
  }, [view]);

  return (
    <FlipContext.Provider value={{ view, twin, toggle }}>{children}</FlipContext.Provider>
  );
}

/** The masthead control. Renders nothing at all on pages with no twin. */
export function FlipToggle() {
  const { view, twin, toggle } = useContext(FlipContext);
  if (!twin) return null;

  return (
    <button
      type="button"
      onClick={toggle}
      title="Flip between the page and its raw Markdown"
      style={{
        font: "inherit",
        fontSize: "0.72rem",
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        fontWeight: 500,
        color: "var(--sounding)",
        background: "none",
        border: "var(--hairline)",
        borderRadius: "999px",
        padding: "0.3rem 0.75rem",
        cursor: "pointer",
        whiteSpace: "nowrap",
      }}
    >
      {view === "agent" ? "Read as human" : "Read as agent"}
    </button>
  );
}

/** Wraps the page. Human view is the children untouched; agent view is the twin. */
export function FlipView({ children }: { children: React.ReactNode }) {
  const { view, twin } = useContext(FlipContext);
  // The loaded text is tagged with the twin route it came from, so navigating
  // to another page never briefly renders the previous route's markdown.
  const [loaded, setLoaded] = useState<{ route: string; body: string } | null>(null);
  // Fetched twins, keyed by route, so flipping back and forth costs one
  // request per page rather than one per flip.
  const cache = useRef(new Map<string, string>());

  useEffect(() => {
    if (view !== "agent" || !twin) return;
    const cached = cache.current.get(twin);
    if (cached !== undefined) {
      setLoaded({ route: twin, body: cached });
      return;
    }
    let stale = false;
    setLoaded(null);
    fetch(twin)
      .then((res) => {
        if (!res.ok) throw new Error(`Failed to fetch ${twin}: ${res.status}`);
        return res.text();
      })
      .then((body) => {
        cache.current.set(twin, body);
        if (!stale) setLoaded({ route: twin, body });
      })
      .catch(() => {
        if (!stale)
          setLoaded({ route: twin, body: `Could not fetch ${twin} — an agent would retry.` });
      });
    return () => {
      stale = true;
    };
  }, [view, twin]);

  if (view !== "agent" || !twin) return <>{children}</>;

  // No chrome beyond one caption: the point of this side is that there is
  // nothing between the reader and the bytes.
  return (
    <div className="shell" style={{ paddingBlock: "2rem 4rem" }}>
      <p
        style={{
          margin: "0 0 1.2rem",
          fontSize: "0.82rem",
          color: "var(--sounding)",
        }}
      >
        This is verbatim what an agent installs.
      </p>
      <pre
        style={{
          margin: 0,
          fontFamily: "var(--font-mono), monospace",
          fontSize: "0.82rem",
          lineHeight: 1.65,
          whiteSpace: "pre-wrap",
          overflowWrap: "anywhere",
        }}
      >
        {loaded?.route === twin ? loaded.body : `Fetching ${twin}…`}
      </pre>
    </div>
  );
}
