import { record } from "./internal/ledger";

export function charge(cents: number): number {
  return record(cents);
}
