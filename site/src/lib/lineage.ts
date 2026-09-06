import { getSkills, type Skill } from "./skills";

/**
 * Where each shipped skill came from, read from its own Attribution section so
 * the hero's counts cannot rot when a skill is added or moved. A skill that
 * links Matt Pocock's repo is his; one that links pstack (Lauren Tan) without
 * Matt is hers; anything else is the maker's own. A skill whose attribution
 * only mentions a source without deriving from it (huh shares Matt's trigger
 * and nothing else) says so with `<!-- lineage: own -->`, which wins over the
 * link rule. scripts/check_lineage_counts.py mirrors both rules and holds the
 * README's sentence to the same numbers.
 */

export type Lineage = "matt" | "tan" | "own";

const MATT = "github.com/mattpocock";
const TAN = /github\.com\/cursor\/plugins|Lauren Tan/;

function attribution(body: string): string {
  const start = body.search(/^## Attribution\s*$/m);
  if (start === -1) return "";
  const rest = body.slice(start + "## Attribution".length);
  const next = rest.search(/^## /m);
  return next === -1 ? rest : rest.slice(0, next);
}

export function lineageOf(skill: Skill): Lineage {
  const text = attribution(skill.body);
  const declared = text.match(/<!--\s*lineage:\s*(matt|tan|own)\s*-->/);
  if (declared) return declared[1] as Lineage;
  if (text.includes(MATT)) return "matt";
  if (TAN.test(text)) return "tan";
  return "own";
}

export function lineageCounts(): Record<Lineage, number> {
  const counts: Record<Lineage, number> = { matt: 0, tan: 0, own: 0 };
  for (const skill of getSkills()) counts[lineageOf(skill)] += 1;
  return counts;
}

const WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"];

/** Prose numbers up to twenty, digits past that; capitalised at a sentence start. */
export function numberWord(n: number, capital = false): string {
  const word = WORDS[n] ?? String(n);
  return capital ? word[0].toUpperCase() + word.slice(1) : word;
}
