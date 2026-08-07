/**
 * Structured data — the same facts the page already states, in a form a machine
 * can read.
 *
 * Two rules, both inherited from the rest of the site:
 *
 *  1. Nothing here asserts anything the visible page does not. Schema that
 *     disagrees with the page is worse than no schema: search engines treat the
 *     mismatch as a quality signal against you, and it is a lie either way.
 *
 *  2. Every date is a real one. `LEGEND_REVISED` is bumped by hand when the
 *     glossary is edited, the way `checked:` works on a survey and on an
 *     instrument card. A date derived from the build would say "revised today"
 *     forever, which is the specific failure this site exists to point at.
 */

export const SITE_URL = "https://clickai.dev";
export const SITE_NAME = "Click AI";

/**
 * The maker, referenced by @id from every other node so the graph resolves to
 * one person rather than sixty-three unrelated strings called "Tim Harris".
 */
export const AUTHOR_ID = `${SITE_URL}/work#person`;

export const PERSON = {
  "@type": "Person",
  "@id": AUTHOR_ID,
  name: "Tim Harris",
  url: `${SITE_URL}/work`,
  description:
    "Builds product and ships software by directing AI coding agents. Maker of ModelDeck, Panely, HiveRunner, and the Click AI skills catalog.",
  sameAs: [
    "https://github.com/timharris707",
    "https://x.com/timharris707",
    "https://modeldeck.ai",
    "https://panely.ai",
    "https://hiverunner.ai",
  ],
};

/** A bare reference to the person above, for use inside other nodes. */
export const AUTHOR_REF = { "@id": AUTHOR_ID };

/**
 * Last hand-revision of `legend.ts`, in ISO form. Taken from that file's git
 * history rather than guessed. Bump it when the glossary changes.
 */
export const LEGEND_REVISED = "2026-08-05";

/** Wraps a node set in the envelope schema.org expects. */
export function graph(...nodes: object[]) {
  return { "@context": "https://schema.org", "@graph": nodes };
}

export function articleNode(note: {
  slug: string;
  title: string;
  standfirst: string;
  date: string;
  checked?: string;
}) {
  return {
    "@type": "Article",
    "@id": `${SITE_URL}/notes/${note.slug}#article`,
    headline: note.title,
    description: note.standfirst,
    url: `${SITE_URL}/notes/${note.slug}`,
    datePublished: note.date,
    // A survey's credibility is the freshness of its claims, so a re-check is a
    // modification even when no prose changed.
    dateModified: note.checked ?? note.date,
    author: AUTHOR_REF,
    publisher: AUTHOR_REF,
    isPartOf: { "@id": `${SITE_URL}/#website` },
    inLanguage: "en",
  };
}

export function definedTermNode(entry: {
  slug: string;
  term: string;
  gloss: string;
  group: string;
}) {
  return {
    "@type": "DefinedTerm",
    "@id": `${SITE_URL}/legend/${entry.slug}#term`,
    name: entry.term,
    description: entry.gloss,
    url: `${SITE_URL}/legend/${entry.slug}`,
    termCode: entry.slug,
    inDefinedTermSet: { "@id": `${SITE_URL}/legend#set` },
  };
}

export const DEFINED_TERM_SET = {
  "@type": "DefinedTermSet",
  "@id": `${SITE_URL}/legend#set`,
  name: "The Legend — agentic-coding vocabulary",
  description:
    "A working glossary of agentic-coding terms, each graded by how much evidence stands behind the claim rather than by how often the word is used.",
  url: `${SITE_URL}/legend`,
  author: AUTHOR_REF,
  dateModified: LEGEND_REVISED,
};

export const WEBSITE = {
  "@type": "WebSite",
  "@id": `${SITE_URL}/#website`,
  name: SITE_NAME,
  url: SITE_URL,
  description:
    "Self-contained playbooks any AI agent can read. Install once, invoke by name.",
  author: AUTHOR_REF,
  publisher: AUTHOR_REF,
  inLanguage: "en",
};

/**
 * Renders a JSON-LD block. `data` is serialised, never interpolated raw.
 *
 * `JSON.stringify` leaves `<` alone, so a `</script>` occurring anywhere in a
 * title, standfirst or gloss would close this block early and spill the rest
 * onto the page as markup. Escaping the characters that can open a tag or an
 * entity keeps the payload inert. `\uXXXX` is valid inside a JSON string, so a
 * parser still reads exactly the same values back out.
 */
export function jsonLdProps(data: object) {
  const json = JSON.stringify(data)
    .replace(/</g, "\\u003c")
    .replace(/>/g, "\\u003e")
    .replace(/&/g, "\\u0026");

  return {
    type: "application/ld+json" as const,
    dangerouslySetInnerHTML: { __html: json },
  };
}
