import type { MetadataRoute } from "next";
import { ENTRIES } from "@/lib/legend";
import { getNotes } from "@/lib/notes";
import { getSkills } from "@/lib/skills";

const BASE = "https://clickai.dev";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: BASE, priority: 1 },
    { url: `${BASE}/skills`, priority: 0.9 },
    { url: `${BASE}/legend`, priority: 0.9 },
    { url: `${BASE}/notes`, priority: 0.8 },
    { url: `${BASE}/install`, priority: 0.7 },
    { url: `${BASE}/work`, priority: 0.7 },
    ...getSkills().map((skill) => ({
      url: `${BASE}/skills/${skill.slug}`,
      priority: 0.8,
    })),
    ...ENTRIES.map((entry) => ({
      url: `${BASE}/legend/${entry.slug}`,
      priority: 0.6,
    })),
    ...getNotes().map((note) => ({
      url: `${BASE}/notes/${note.slug}`,
      lastModified: note.checked || note.date,
      priority: 0.7,
    })),
  ];
}
