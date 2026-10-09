import { charge } from "../src/index";
import { fakeLedger } from "../src/testing";
import { sampleCents } from "./fixtures";

export const result = [charge(sampleCents), fakeLedger()()];
