let total = 0;

export function record(cents: number): number {
  total += cents;
  return total;
}
