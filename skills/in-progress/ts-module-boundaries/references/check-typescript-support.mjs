// Runs before depcruise in `lint:boundaries`. dependency-cruiser reads TypeScript
// only through a typescript version inside its supported range; outside it, every
// .ts file is skipped, the cruise finds nothing, and the check passes. Fail loudly
// instead, so a later TypeScript bump cannot turn the merge gate into a pass.
import { getAvailableTranspilers } from "dependency-cruiser";

const ts = getAvailableTranspilers().find((t) => t.name === "typescript");

if (!ts?.available) {
  console.error(
    `dependency-cruiser cannot read TypeScript here: it needs typescript ${ts?.version ?? "in its supported range"}, ` +
      `and the installed version is missing or outside that range. It would skip every .ts file and pass. ` +
      `Install a supported typescript, or upgrade dependency-cruiser.`,
  );
  process.exit(1);
}
