import type { Metadata } from "next";

/**
 * Per-page Open Graph block. Metadata merging is shallow — a page that sets
 * `openGraph` replaces the layout's object wholesale, it does not merge into
 * it — so every page routes through this helper to correct og:url without
 * losing siteName and type. Relative URLs resolve against the metadataBase
 * set in the root layout.
 */
export function openGraph(url: string): Metadata["openGraph"] {
  return { type: "website", siteName: "Click AI", url };
}
