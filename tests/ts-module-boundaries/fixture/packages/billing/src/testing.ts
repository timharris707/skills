import { record } from "./internal/ledger";

export function fakeLedger(): () => number {
  return () => record(0);
}
