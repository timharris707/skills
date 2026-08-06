import type { Metadata } from "next";
import Regions from "@/components/Regions";
import { getCatalog } from "@/lib/catalog";

export const metadata: Metadata = {
  title: "Catalog",
  description: "Every skill in the catalog, by region.",
  alternates: { canonical: "/skills" },
};

export default function Catalog() {
  const { regions, skills } = getCatalog();

  return (
    <>
      <div className="shell" style={{ paddingBlock: "clamp(2.5rem, 6vw, 4rem) 0" }}>
        <p className="eyebrow">The catalog</p>
        <h1 style={{ maxWidth: "16ch" }}>
          {skills.length} skills, in {regions.length} regions.
        </h1>
        <p className="lede">
          Grouped by the job they do, roughly in the order work moves through them —{" "}
          {regions.map((r) => r.name.toLowerCase()).join(", ")}.
        </p>
      </div>
      <Regions regions={regions} />
    </>
  );
}
