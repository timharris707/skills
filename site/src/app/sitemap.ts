import type { MetadataRoute } from "next";
import { getSkills } from "@/lib/skills";

const BASE = "https://clickai.dev";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: BASE, priority: 1 },
    { url: `${BASE}/skills`, priority: 0.9 },
    { url: `${BASE}/install`, priority: 0.7 },
    { url: `${BASE}/work`, priority: 0.7 },
    ...getSkills().map((skill) => ({
      url: `${BASE}/skills/${skill.slug}`,
      priority: 0.8,
    })),
  ];
}
