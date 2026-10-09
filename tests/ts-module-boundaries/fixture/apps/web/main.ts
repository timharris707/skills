import { readFileSync } from "node:fs";
import ts from "typescript";
import { charge } from "@fixture/billing";
import { fakeLedger } from "@fixture/billing/testing";
import { listItems } from "@fixture/catalog";
import type { FakeItem } from "@fixture/catalog/testing";
import { buttonText } from "@fixture/ui";
import { buttonText as relativeText } from "../../packages/ui/src/index";
import type { Legacy } from "./legacy-types";

export type MainLegacy = Legacy;
export type MainItem = FakeItem;
export const main = [readFileSync, ts.version, charge(1), fakeLedger(), listItems(), buttonText(1), relativeText(1)];
