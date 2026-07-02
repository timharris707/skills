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

## Repo-grounded review (`--repo`)

`--repo PATH` lets every seat read a **read-only snapshot** of the repository so findings cite real `path:line` instead of only critiquing the handed-in packet. That widens egress: a grounded seat can quote **any in-scope file** into its reply, that reply is persisted, and in round 2+ it fans out to the *other* providers. So consent can't just "let seats read" — it binds to the repo **scope**, and the disclosure says repo contents can be transmitted.

How the scope is bounded and disclosed:

- **Scope resolution** — the snapshot respects `.gitignore` (via `git ls-files`, with an `os.walk` fallback), always excludes `.git/`, applies a **secret/denylist** per path segment (`.env*`, `*.pem`, the SSH key basenames `id_rsa`/`id_dsa`/`id_ecdsa`/`id_ed25519` — not a bare `id_*` glob, which would eat source files — `*.key`, and `secrets`/`creds`/`token` names), and `realpath`-confines to the root so symlinks pointing outside are dropped. `--repo-include`/`--repo-exclude` globs narrow it further.
- **Hash-bound consent** — the egress consent hash binds to **source-packet-hash + repo-scope-hash** (the manifest of files a seat *could* read). The disclosure surfaces the repo root, file/byte totals, the scope hash, and what was excluded; the y/N prompt names the totals. `repo-scope-manifest.json` records what was in scope at approval. Tiered: `local-only` **forbids** `--repo` with any external seat; `redacted` (default) hash-binds the scope; `public` discloses.
- **Secret-scan before approval** — an advisory secret-scan runs over the in-scope tree and **surfaces its findings before you approve** (it never echoes the full secret). The denylist + `.gitignore` are **not foolproof** (R1): a key the `.gitignore` missed can still land in scope, so review the manifest and the scan output, and treat the residual as a known limit, not zero risk.

The exfil control in gate mode is **network isolation, not read-confinement**:

- **Gate mode requires read XOR network (D4).** A grounded seat that is also networked is exactly the read-then-exfiltrate channel the quarantine exists to break. Gate + `--repo` therefore *requires* every seat to be network-isolatable; a seat that can't be de-networked (today **gemini**, **antigravity**) makes the run **refuse** (named as a labeled NO-GO), rather than running with only a warning. Advisory + `--repo` is allowed for your own repo with a loud disclosure — you own that risk.
- **The snapshot bounds consent/verify, not physical reads (R9).** Be honest about this: codex's `--sandbox read-only` does **not** confine reads to its working directory — it can read files *outside* the snapshot (observed in a real run reading a file from its host home dir). So the snapshot bounds what is **hashed, disclosed, and verified against**, not what a seat can physically read off the machine. Exfil is still blocked because codex is network-isolated under gate+`--repo` (D4); the residual is a seat quoting an out-of-scope file into an artifact, countered by the secret denylist and the output secret-scan. Don't claim a read-confinement the system doesn't have.

## Persisted run artifacts

Run artifacts persist by default under `~/.advisory-board/runs/<slug>-<date>/` (v1.11) instead of an ephemeral `/tmp` folder. Persistence changes **where artifacts sit on the local disk — nothing else**: the artifacts inherit the run's sensitivity handling exactly as decided above. A local-only run's artifacts are still local-only material; a redacted run's artifacts contain only the redacted bytes the consent hash covered. Nothing new egresses — `history` and the runs root are pure local disk reads, and no provider ever receives an artifact because it persisted. What changes in practice is *lifetime*: sensitive material now outlives the reboot that used to clean `/tmp`, so treat the runs root with the same care as the source material, and prefer `--ephemeral` (a throwaway `/tmp` run) or a deliberate `--out`/`--runs-root` location when the run's material shouldn't linger on disk.

Since v1.12 the run dir also holds `source-material.txt` — an exact copy of the reviewed source, written post-approval so a later `--revise` can diff against it. It is the same bytes the persisted `prompts/*.prompt` already embed: the same consent envelope, the same sensitivity handling, no new exposure class.

The same category covers **board-generated derivatives fanned out between seats** — the round-2 cross-reading packet sends each seat the *other* seats' round-1 reviews, and the v1.13 endorsement pass (`--output revised-draft`) sends the non-revision board seats the source plus the board-**generated** revised draft and change tables to vote on. Those derivatives are freshly produced by the board, not bytes a seat already received, but they egress only to seats already on the board under the run's existing disclosure — the same consent envelope, the same sensitivity handling, no new exposure class.

## Always

Never write secrets into any artifact. Redact keys, tokens, cookies, and private environment values from prompts, packets, metadata, and the handoff.
