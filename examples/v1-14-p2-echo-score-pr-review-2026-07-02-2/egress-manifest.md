# Egress Manifest — v1.14 p2 echo score pr review

This run will send the bytes below to external providers. Review before approving.

Packet content hash (sha256): 02f980349bad97507b431dada739865c28d9f2c2adb3bf2a92af2a251266f54d
Sensitivity: redacted
Mode: advisory
Consent: hash-bound approval required (non-public material blocks until approved)

## Prior-run revision context (--revise)

Revises: ~/.advisory-board/runs/v1-14-p2-echo-score-pr-review-2026-07-02
Injected into every round-1 prompt (inside the packet content hash): prior verdict digest + source diff (prior source: source-material.txt, sha-verified) — 43511 bytes.
Prior run sensitivity: redacted

## Files leaving this machine

| File                          | Bytes | Lines | Goes to |
| ----------------------------- | ----- | ----- | ------- |
| prompts/claude-round-1.prompt | 153897 |  2116 | Anthropic (claude) |
| prompts/codex-round-1.prompt  | 153751 |  2114 | OpenAI (codex) |

## Providers

- Anthropic (claude) — receives prompts/claude-round-1.prompt
- OpenAI (codex) — receives prompts/codex-round-1.prompt

Approval: <PENDING — bound to the content hash above>
