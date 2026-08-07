import type { MetadataRoute } from "next";
import { ENTRIES } from "@/lib/legend";
import { getNotes } from "@/lib/notes";
import { getSkills } from "@/lib/skills";
import { LEGEND_REVISED } from "@/lib/schema";

const BASE = "https://clickai.dev";

/*
 * `lastModified` appears only where a real date exists — the glossary's hand-set
 * revision date and a note's own dates. The static pages and the generated skill
 * pages carry none, because the only date available for them would be the build
 * clock, and a sitemap that claims every page changed on every deploy teaches a
 * crawler to stop believing the field.
 */

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: BASE, priority: 1 },
    { url: `${BASE}/skills`, priority: 0.9 },
    { url: `${BASE}/legend`, lastModified: LEGEND_REVISED, priority: 0.9 },
    { url: `${BASE}/notes`, priority: 0.8 },
    { url: `${BASE}/install`, priority: 0.7 },
    { url: `${BASE}/work`, priority: 0.7 },
    { url: `${BASE}/instruments`, priority: 0.7 },
    ...getSkills().map((skill) => ({
      url: `${BASE}/skills/${skill.slug}`,
      priority: 0.8,
    })),
    ...ENTRIES.map((entry) => ({
      url: `${BASE}/legend/${entry.slug}`,
      lastModified: LEGEND_REVISED,
      priority: 0.6,
    })),
    ...getNotes().map((note) => ({
      url: `${BASE}/notes/${note.slug}`,
      lastModified: note.checked || note.date,
      priority: 0.7,
    })),
  ];
}
