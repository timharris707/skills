# Egress Manifest — v1.13 fixit revision artifact design brief

This run will send the bytes below to external providers. Review before approving.

Packet content hash (sha256): 40f3be4a4eff26a3e07d256c4975f9d444228839d52984583ddc1ead7c27759b
Sensitivity: redacted
Mode: advisory
Consent: hash-bound approval required (non-public material blocks until approved)

## Files leaving this machine

| File                          | Bytes | Lines | Goes to |
| ----------------------------- | ----- | ----- | ------- |
| prompts/claude-round-1.prompt | 18946 |   175 | Anthropic (claude) |
| prompts/codex-round-1.prompt  | 18800 |   173 | OpenAI (codex) |
| prompts/gemini-round-1.prompt | 18799 |   173 | Google (gemini) |

## Providers

- Anthropic (claude) — receives prompts/claude-round-1.prompt
- OpenAI (codex) — receives prompts/codex-round-1.prompt
- Google (gemini) — receives prompts/gemini-round-1.prompt

Approval: <PENDING — bound to the content hash above>
