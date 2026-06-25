# Data Handling

A board sends the **same source material to every seat's provider** — by default Anthropic, OpenAI, and Google. Treat that as an outbound disclosure and handle it before launching, not after.

## Disclose before the first call

If the material is anything but already-public, tell the user plainly what will leave the machine and to whom, and get a go-ahead:

> This review sends your source material to Anthropic (Claude), OpenAI (Codex), and Google (Gemini). Proceed?

Name only the providers actually in the lineup.

## Decide the handling

1. **Public / low-sensitivity** → proceed normally.
2. **Sensitive but reviewable** → redact before building the source packet (see below), then proceed.
3. **Must-not-leave** (regulated data, secrets, privileged material) → use a **local-only board**: every seat a local/offline model, or don't run the board. Never silently send it.

## Redaction checklist

When redacting the source packet, strip or mask: credentials, tokens, API keys, cookies; personal data (names, emails, IDs) not needed for the review; customer or third-party identifiers; internal hostnames and infra secrets. Redact once in the shared source packet so every seat sees the same redacted bytes.

## Local-only mode

Swap each seat's CLI for a local model runner. The `ollama` seat is registered for exactly this (`--board ...,ollama`, `--model ollama=<model>`): it carries `provider: local`, so the conductor never egresses its prompt and excludes it from the egress manifest and the disclosure — the material stays on the machine. The protocol, lenses, rounds, and artifacts are unchanged — only the model endpoints differ. A local board trades some reasoning strength for keeping the material on the machine; say so in the handoff. Record the mode in `run-metadata.md`.

## Always

Never write secrets into any artifact. Redact keys, tokens, cookies, and private environment values from prompts, packets, metadata, and the handoff.
