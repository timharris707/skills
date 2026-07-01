# Run Metadata Template

Copy into `run-metadata.md` for the run and fill it in. This is the provenance the handoff cites — record what *actually* happened, not what was requested. Never include secrets.

```text
# Run Metadata — <title>

Date: <YYYY-MM-DD>   ·   Rounds run: <n>   ·   Cross-reading: none | summaries | full
Output: quick verdict | full handoff | implementation sequence
Lens preset: <preset, or "custom">

## Seats

| Seat   | Lens          | Model requested | Model that answered | Reasoning/effort | Auth mode    | Status            |
| ------ | ------------- | --------------- | ------------------- | ---------------- | ------------ | ----------------- |
| Claude | architecture  | claude-fable-5  | <id returned>       | max              | subscription | ran               |
| Codex  | impl/testing  | gpt-5.5         | <id returned>       | xhigh            | subscription | ran               |
| Gemini | product/ops   | <model>         | <id returned>       | HIGH             | subscription | dropped @ round 2 |

Status is one of: ran · degraded · dropped @ round N. A board needs >= 2 seats that ran.

## Source

Access method: shared path | single source packet
Source: <paths / repo @ commit / URL / packet file>
Sensitivity & handling: public | redacted | local-only   (see references/data-handling.md)

## Run

| Stage   | Started | Finished | Wall-clock | Tokens in/out (if known) |
| ------- | ------- | -------- | ---------- | ------------------------ |
| Round 1 |         |          |            |                          |
| Round 2 |         |          |            |                          |
| Synth   |         |          |            |                          |

Preflight: <go/no-go per seat>
Commands: <the exact CLI invocations, flags included; no secrets>
Notes: <substitutions, e.g. "requested gpt-5.5, ran gpt-5.1 — newer unavailable">
```

Capture the model that *answered*, not just the one requested: model names drift and CLIs silently fall back. The verdict is only as trustworthy as knowing exactly who voted.
