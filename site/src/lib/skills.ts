import fs from "node:fs";
import path from "node:path";

/**
 * The site is generated from the repository's SKILL.md files, so the catalog
 * cannot drift from what actually ships. Nothing here is hand-maintained: add a
 * skill directory and it appears, with the same description installers see.
 */

const REPO_ROOT = path.join(process.cwd(), "..");
const SKILLS_DIR = path.join(REPO_ROOT, "skills");
const BUCKETS_FILE = path.join(SKILLS_DIR, "buckets.json");
const MARKETPLACE = path.join(REPO_ROOT, ".claude-plugin", "marketplace.json");

export type Bucket = {
  id: string;
  name: string;
  promoted: boolean;
  blurb: string;
};

export type Skill = {
  slug: string;
  name: string;
  description: string;
  /** The SKILL.md body with frontmatter stripped. */
  body: string;
  /** The bucket directory it lives in — its category and its promotion status. */
  bucket: string;
  /** The plugin that ships it, from marketplace.json. */
  plugin: string;
  pluginVersion: string;
  /**
   * "pack" when its plugin ships more than one skill, "standalone" when it
   * ships alone — derived from the plugin's own skill count, so a plugin
   * cannot claim a skill without its badge coming out correct.
   */
  shipsAs: "pack" | "standalone";
  /** Files beside SKILL.md — references/, scripts/, agents/. */
  extras: string[];
  githubUrl: string;
};

type Plugin = {
  name: string;
  version: string;
  description: string;
  skills: string[];
};

/**
 * Parse the leading `---` block. SKILL.md frontmatter is flat `key: value`
 * pairs, so this stays dependency-free rather than pulling in a YAML engine.
 */
function parseFrontmatter(raw: string): { data: Record<string, string>; body: string } {
  if (!raw.startsWith("---")) return { data: {}, body: raw };
  const end = raw.indexOf("\n---", 3);
  if (end === -1) return { data: {}, body: raw };

  const block = raw.slice(3, end);
  const body = raw.slice(end + 4).replace(/^\r?\n/, "");
  const data: Record<string, string> = {};

  for (const line of block.split("\n")) {
    const match = line.match(/^([A-Za-z][\w-]*):\s*(.*)$/);
    if (!match) continue;
    let value = match[2].trim();
    // Descriptions containing a colon are quoted in some skills. CI's
    // check_skill_frontmatter.py guarantees double-quoted values are JSON
    // strings, so JSON.parse decodes every escape; fall back to a bare
    // unquote rather than crash the build on a file CI hasn't seen yet.
    if (value.startsWith('"') && value.endsWith('"')) {
      try {
        value = JSON.parse(value);
      } catch {
        value = value.slice(1, -1);
      }
    } else if (value.startsWith("'") && value.endsWith("'")) {
      value = value.slice(1, -1);
    }
    data[match[1]] = value;
  }
  return { data, body };
}

function readMarketplace(): Plugin[] {
  const parsed = JSON.parse(fs.readFileSync(MARKETPLACE, "utf8"));
  return (parsed.plugins ?? []).map((p: Plugin) => ({
    name: p.name,
    version: p.version,
    description: p.description,
    skills: (p.skills ?? []).map((s: string) => s.replace(/^\.\//, "").replace(/\/$/, "")),
  }));
}

/** Local build artefacts that exist on a dev machine but are never shipped. */
const IGNORED = /^(__pycache__|node_modules|\.DS_Store)$|\.pyc$/;

/**
 * What ships beside SKILL.md, summarised for reading rather than enumerated.
 * Top-level files by name; directories as a name and a count — advisory-board
 * alone carries 130+ files, and a wall of paths is noise in a sidebar and worse
 * in the Markdown twin an agent fetches.
 */
function listExtras(dir: string): string[] {
  const countFiles = (current: string): number => {
    let n = 0;
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      if (IGNORED.test(entry.name)) continue;
      n += entry.isDirectory() ? countFiles(path.join(current, entry.name)) : 1;
    }
    return n;
  };

  const out: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) =>
    a.name.localeCompare(b.name),
  )) {
    if (entry.name === "SKILL.md" || entry.name.startsWith(".") || IGNORED.test(entry.name)) continue;
    if (entry.isDirectory()) {
      const n = countFiles(path.join(dir, entry.name));
      if (n > 0) out.push(`${entry.name}/ — ${n} file${n === 1 ? "" : "s"}`);
    } else {
      out.push(entry.name);
    }
  }
  return out;
}

let bucketCache: Bucket[] | null = null;

/** Every declared bucket, promoted or not. */
export function getBuckets(): Bucket[] {
  if (!bucketCache) {
    bucketCache = JSON.parse(fs.readFileSync(BUCKETS_FILE, "utf8")).buckets as Bucket[];
  }
  return bucketCache;
}

let cache: Skill[] | null = null;

/**
 * Every skill in a **promoted** bucket. Unpromoted buckets — in-progress, misc,
 * deprecated — are the whole point of the layout: a half-built skill parked
 * there drops off the site and out of the marketplace in one `git mv`, with no
 * other edit and no deletion.
 */
export function getSkills(): Skill[] {
  if (cache) return cache;

  const plugins = readMarketplace();
  const owners = new Map<string, Plugin>();
  for (const plugin of plugins) {
    for (const rel of plugin.skills) owners.set(rel, plugin);
  }

  const skills: Skill[] = [];
  for (const bucket of getBuckets()) {
    if (!bucket.promoted) continue;
    const bucketDir = path.join(SKILLS_DIR, bucket.id);
    if (!fs.existsSync(bucketDir)) continue;

    for (const entry of fs.readdirSync(bucketDir, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const dir = path.join(bucketDir, entry.name);
      const skillFile = path.join(dir, "SKILL.md");
      if (!fs.existsSync(skillFile)) continue;

      const rel = `skills/${bucket.id}/${entry.name}`;
      const { data, body } = parseFrontmatter(fs.readFileSync(skillFile, "utf8"));
      const owner = owners.get(rel);

      skills.push({
        slug: entry.name,
        name: data.name ?? entry.name,
        description: data.description ?? "",
        body,
        bucket: bucket.id,
        plugin: owner?.name ?? "unpublished",
        pluginVersion: owner?.version ?? "",
        shipsAs: (owner?.skills.length ?? 0) > 1 ? "pack" : "standalone",
        extras: listExtras(dir),
        githubUrl: `https://github.com/timharris707/skills/blob/main/${rel}/SKILL.md`,
      });
    }
  }

  cache = skills.sort((a, b) => a.slug.localeCompare(b.slug));
  return cache;
}

export function getSkill(slug: string): Skill | undefined {
  return getSkills().find((s) => s.slug === slug);
}

export function getPlugins(): Plugin[] {
  return readMarketplace();
}

/** The independent, generated Codex desktop edition. */
export function getCodexPlugin() {
  const plugin = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, "plugins/clickai-codex/.codex-plugin/plugin.json"), "utf8"));
  const marketplace = JSON.parse(fs.readFileSync(path.join(REPO_ROOT, ".agents/plugins/marketplace.json"), "utf8"));
  return { name: plugin.name as string, version: plugin.version as string, marketplace: marketplace.name as string, skills: plugin.skills.length as number };
}

export type Edition = "claude" | "codex";

/** Reuse the catalog identity while reading each edition's actual installed text. */
export function getEditionSkill(slug: string, edition: Edition): Skill | undefined {
  const original = getSkill(slug);
  if (!original || edition === "claude") return original;
  const rel = `plugins/clickai-codex/skills/${original.bucket}/${slug}`;
  const dir = path.join(REPO_ROOT, rel);
  // A catalog skill missing its generated edition is a broken publication, so fail the build.
  const { data, body } = parseFrontmatter(fs.readFileSync(path.join(dir, "SKILL.md"), "utf8"));
  const plugin = getCodexPlugin();
  return { ...original, name: data.name ?? slug, description: data.description ?? "", body,
    plugin: plugin.name, pluginVersion: plugin.version, shipsAs: "pack", extras: listExtras(dir),
    githubUrl: `https://github.com/timharris707/skills/blob/main/${rel}/SKILL.md` };
}
