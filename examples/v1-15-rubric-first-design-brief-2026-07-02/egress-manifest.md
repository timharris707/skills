# Egress Manifest — v1.15 rubric first design brief

This run will send the bytes below to external providers. Review before approving.

Packet content hash (sha256): 11d214bd9b1f3229d989821732138eb760f24bcb21cb5728f279fb3b4f8a4496
Sensitivity: redacted
Mode: advisory
Consent: hash-bound approval required (non-public material blocks until approved)

## Files leaving this machine

| File                          | Bytes | Lines | Goes to |
| ----------------------------- | ----- | ----- | ------- |
| prompts/claude-round-1.prompt | 25000 |   164 | Anthropic (claude) |
| prompts/codex-round-1.prompt  | 24854 |   162 | OpenAI (codex) |
| prompts/gemini-round-1.prompt | 24853 |   162 | Google (gemini) |

## Providers

- Anthropic (claude) — receives prompts/claude-round-1.prompt
- OpenAI (codex) — receives prompts/codex-round-1.prompt
- Google (gemini) — receives prompts/gemini-round-1.prompt

Approval: <PENDING — bound to the content hash above>
