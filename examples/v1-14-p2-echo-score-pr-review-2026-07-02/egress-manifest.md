# Egress Manifest — v1.14 p2 echo score pr review

This run will send the bytes below to external providers. Review before approving.

Packet content hash (sha256): 063e2a23b28b9c290e95ae5a57313dbf1231e0a48932a71cbaf03069e2606c7d
Sensitivity: redacted
Mode: advisory
Consent: hash-bound approval required (non-public material blocks until approved)

## Files leaving this machine

| File                          | Bytes | Lines | Goes to |
| ----------------------------- | ----- | ----- | ------- |
| prompts/claude-round-1.prompt | 90897 |  1376 | Anthropic (claude) |
| prompts/codex-round-1.prompt  | 90751 |  1374 | OpenAI (codex) |

## Providers

- Anthropic (claude) — receives prompts/claude-round-1.prompt
- OpenAI (codex) — receives prompts/codex-round-1.prompt

Approval: <PENDING — bound to the content hash above>
