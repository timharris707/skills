# Egress Manifest — Payments API idempotency keys

This run will send the bytes below to external providers. Review before approving.

Packet content hash (sha256): 56d6bf7af7a3ae9d5c7da1149a2f54a1001518a917a6fd9e41f562b2db37a607
Sensitivity: public
Mode: gate
Consent: disclosure (clearly-public material proceeds after disclosure is shown)

⚠ NETWORK NOT ISOLATED for: gemini — gate mode cannot remove these seats' network (no CLI flag disables their web/grounding tools), so a prompt injection in the source could still drive them to fetch or exfiltrate. Treat them as networked.

## Files leaving this machine

| File                          | Bytes | Lines | Goes to |
| ----------------------------- | ----- | ----- | ------- |
| prompts/claude-round-1.prompt |  1567 |    33 | Anthropic (claude) |
| prompts/codex-round-1.prompt  |  1421 |    31 | OpenAI (codex) |
| prompts/gemini-round-1.prompt |  1420 |    31 | Google (gemini) |

## Providers

- Anthropic (claude) — receives prompts/claude-round-1.prompt
- OpenAI (codex) — receives prompts/codex-round-1.prompt
- Google (gemini) — receives prompts/gemini-round-1.prompt

Approval: <PENDING — bound to the content hash above>
