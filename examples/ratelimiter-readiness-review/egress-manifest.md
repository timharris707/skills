# Egress Manifest — review packet

This run will send the bytes below to external providers. Review before approving.

Packet content hash (sha256): 2ca8c659997d8d3344f6fdd6800706cc76d706492123b210d76cfc1f783f3525
Sensitivity: public
Mode: gate
Consent: disclosure (clearly-public material proceeds after disclosure is shown)

⚠ NETWORK NOT ISOLATED for: gemini — gate mode cannot remove these seats' network (no CLI flag disables their web/grounding tools), so a prompt injection in the source could still drive them to fetch or exfiltrate. Treat them as networked.

## Files leaving this machine

| File                          | Bytes | Lines | Goes to |
| ----------------------------- | ----- | ----- | ------- |
| prompts/claude-round-1.prompt |  5580 |   151 | Anthropic (claude) |
| prompts/codex-round-1.prompt  |  5434 |   149 | OpenAI (codex) |
| prompts/gemini-round-1.prompt |  5433 |   149 | Google (gemini) |

## Providers

- Anthropic (claude) — receives prompts/claude-round-1.prompt
- OpenAI (codex) — receives prompts/codex-round-1.prompt
- Google (gemini) — receives prompts/gemini-round-1.prompt

Approval: <PENDING — bound to the content hash above>
