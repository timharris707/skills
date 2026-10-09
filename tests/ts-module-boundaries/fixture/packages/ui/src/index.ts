import { charge } from "@fixture/billing";
import { label } from "./internal/button";

export function buttonText(cents: number): string {
  return `${label()} ${charge(cents)}`;
}
