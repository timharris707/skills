"""The egress packet + gate (design §8, §12): packet assembly (round 1 and
round 2), the content hash, tiered consent, the manifest, and the hash-bound
pre-spawn hard stop."""
from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from typing import Optional

from _conductor.constants import now_stamp
from _conductor.config import RunConfig
from _conductor.grounding import render_repo_scope_lines
from _conductor.prompts import (
    build_round1_prompt,
    build_round2_packet,
    build_round2_prompt,
)

__all__ = [
    "build_round2",
    "PacketBlob",
    "build_packet",
    "packet_hash",
    "EgressApproval",
    "render_egress_manifest",
    "CONSENT_TOKENS",
    "CONSENT_PROSE",
    "consent_token",
    "consent_mode_for",
    "disclosure_line",
    "unenforced_network_note",
    "_d4_refusal_detail",
    "enforce_egress_gate",
]


def build_round2(config: RunConfig, prev_results: list, round_no: int = 2) -> tuple:
    """Build round `round_no`'s egress blobs (one per seat USABLE in the previous
    round) + the shared board packet, from `prev_results` (round_no − 1's results).
    A seat that dropped in the previous round has no review to build on, so it does
    not continue (recorded as such). `round_no` defaults to 2 so existing callers
    are unchanged; `--rounds auto` (M1) calls it for round 3, 4, … as well."""
    usable = [r for r in prev_results if r.usable]
    repo_lines = config.grounding.content_lines if config.grounding is not None else None
    board_packet = build_round2_packet(usable, config.cross_reading, round_no=round_no,
                                       repo_lines=repo_lines)
    by_id = {s.id: s for s in config.board}
    own = {r.seat: r.stdout for r in usable}
    blobs: list = []
    for r in usable:
        seat = by_id[r.seat]
        prompt = build_round2_prompt(seat, config.source.text,
                                     board_packet=board_packet,
                                     own_review=own[r.seat],
                                     cross_reading=config.cross_reading,
                                     round_no=round_no,
                                     grounded=config.grounded)
        blobs.append(PacketBlob(
            seat=seat.id,
            provider=seat.provider,
            relpath=f"prompts/{seat.id}-round-{round_no}.prompt",
            text=prompt,
        ))
    return blobs, board_packet


# Egress packet (design §8, §12)


@dataclass
class PacketBlob:
    seat: str
    provider: str
    relpath: str
    text: str

    @property
    def data(self) -> bytes:
        return self.text.encode("utf-8")

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()

    @property
    def nbytes(self) -> int:
        return len(self.data)

    @property
    def nlines(self) -> int:
        return self.text.count("\n") + (1 if self.text and not self.text.endswith("\n") else 0)


def build_packet(config: RunConfig) -> list:
    """Materialize the exact per-seat round-1 prompts that would leave the machine.
    On a --revise run the prompts embed the revision material (prior-verdict
    digest + source diff), so the packet hash — and therefore consent — covers
    every injected byte with no extra machinery."""
    blobs: list = []
    revision_material = config.revision.material if config.revision else None
    for seat in config.board:
        prompt = build_round1_prompt(seat, config.source.text, grounded=config.grounded,
                                     revision_material=revision_material)
        blobs.append(PacketBlob(
            seat=seat.id,
            provider=seat.provider,
            relpath=f"prompts/{seat.id}-round-1.prompt",
            text=prompt,
        ))
    return blobs


def packet_hash(blobs: list) -> str:
    """A single content hash binding consent to the exact outbound bytes.

    Order-independent: hash each blob's relpath + content hash, sorted, so the
    manifest hash is stable regardless of seat ordering.
    """
    digest = hashlib.sha256()
    for line in sorted(f"{b.relpath}\n{b.sha256}\n" for b in blobs):
        digest.update(line.encode("utf-8"))
    return digest.hexdigest()


# Egress gate (design §8) — consent bound to a content hash; pre-spawn hard stop


@dataclass
class EgressApproval:
    approved: bool
    mode: str            # disclosure | hash-bound | refused | override | skipped
    content_hash: str
    timestamp: str
    detail: str
    # Repo-grounding (P2): when the run is grounded, consent binds to the prompt
    # packet hash AND this scope hash (the manifest of files a seat could read). None
    # for an ungrounded run, so its recorded approval is byte-identical to before.
    scope_hash: Optional[str] = None


def render_egress_manifest(config: RunConfig, blobs: list, content_hash: str) -> str:
    consent = consent_mode_for(config.sensitivity)
    # Only external blobs actually leave the machine; a local seat (provider="local",
    # e.g. ollama) is materialized on disk but never egresses, so it must NOT appear
    # under "Files leaving this machine". Split them up front so even the intro line
    # never overstates what egresses (a fully-local board sends nothing).
    external = sorted((b for b in blobs if b.provider != "local"), key=lambda x: x.relpath)
    local = sorted((b for b in blobs if b.provider == "local"), key=lambda x: x.relpath)
    intro = ("This run will send the bytes below to external providers. Review before approving."
             if external else
             "This run sends NOTHING to external providers (local-only board); the prompts below "
             "stay on this machine.")
    lines = [
        f"# Egress Manifest — {config.title}",
        "",
        intro,
        "",
        f"Packet content hash (sha256): {content_hash}",
        f"Sensitivity: {config.sensitivity}",
        f"Mode: {config.mode}",
        f"Consent: {consent}",
    ]
    if config.grounding is not None:
        lines.append(f"Repo scope hash (sha256): {config.grounding.scope_hash}")
    note = unenforced_network_note(config)
    if note:
        lines += ["", note]
    if config.grounding is not None:
        # Repo-grounding widens egress: a seat can read & quote any in-scope file, and
        # round 2+ fans that reply out to the OTHER providers. Disclose the exact read
        # surface consent binds to (§8: the manifest must never understate egress).
        lines += ["", "## Readable repository scope", "",
                  "Seats may READ & QUOTE any file below; quotes can be transmitted to the "
                  "external providers and fan out to the other seats in round 2+.", ""]
        lines += render_repo_scope_lines(config.grounding)
    if config.revision is not None:
        # --revise widens the packet: prior-run material rides inside the round-1
        # prompts. Disclose it HERE, on the consent surface itself, like grounding
        # does (§8) — the bytes are already inside the content hash above.
        r = config.revision
        lines += ["", "## Prior-run revision context (--revise)", "",
                  f"Revises: {r.run_dir}",
                  f"Injected into every round-1 prompt (inside the packet content hash): "
                  f"{r.note} — {len(r.material.encode('utf-8'))} bytes.",
                  "Prior run sensitivity: "
                  + (r.prior_sensitivity or "unknown (no readable sensitivity.json)")]
    if config.ask is not None:
        # `ask` carries a NEW question + run-context bytes to the addressed seat(s).
        # Disclose it HERE on the consent surface (§8) — the bytes are already inside
        # the content hash above.
        a = config.ask
        material = ("the recovered reviewed material" if a.source_recovered_from
                    else "the reviewed material could NOT be recovered")
        lines += ["", "## Post-verdict question (ask)", "",
                  f"Run questioned: {a.run_dir}",
                  f"Addressed seats: {', '.join(s.id for s in config.board)}",
                  f"Question ({len(a.question.encode('utf-8'))} bytes): {a.question}",
                  f"Each addressed seat's prompt carries this question, a mechanical "
                  f"digest of the prior verdict, that seat's own prior review, and "
                  f"{material} — all inside the packet content hash above."]
    lines += [
        "",
        "## Files leaving this machine",
        "",
        "| File                          | Bytes | Lines | Goes to |",
        "| ----------------------------- | ----- | ----- | ------- |",
    ]
    if external:
        for b in external:
            lines.append(f"| {b.relpath:<29} | {b.nbytes:>5} | {b.nlines:>5} | {b.provider} ({b.seat}) |")
    else:
        lines.append("| (none — local-only board)     |       |       |         |")
    if local:
        lines += ["", "## Stays on this machine (local seats — no egress)", ""]
        for b in local:
            lines.append(f"- {b.relpath} — {b.seat} (local model, on-machine; never sent)")
    lines += ["", "## Providers", ""]
    if external:
        for b in external:
            lines.append(f"- {b.provider} ({b.seat}) — receives {b.relpath}")
    else:
        lines.append("- (none — no external providers receive any bytes)")
    binding = "content+scope hash" if config.grounding is not None else "content hash"
    lines += ["", f"Approval: <PENDING — bound to the {binding} above>"]
    return "\n".join(lines) + "\n"


# Stable machine tokens for the tiered consent model (decision #2). The token is
# the source of truth for sensitivity.json; the prose is derived from it, never
# the other way around (a reword must not silently change the machine field).
CONSENT_TOKENS = {"public": "disclosure", "redacted": "hash-bound", "local-only": "refused"}
CONSENT_PROSE = {
    "disclosure": "disclosure (clearly-public material proceeds after disclosure is shown)",
    "hash-bound": "hash-bound approval required (non-public material blocks until approved)",
    "refused": "refused (must-not-leave material cannot go to external providers)",
}


def consent_token(sensitivity: str) -> str:
    return CONSENT_TOKENS.get(sensitivity, "hash-bound")


def consent_mode_for(sensitivity: str) -> str:
    return CONSENT_PROSE[consent_token(sensitivity)]


def disclosure_line(config: RunConfig) -> str:
    providers = sorted({seat.provider for seat in config.board if seat.provider != "local"})
    if not providers:
        if config.grounding is not None:
            return ("This run sends nothing to external providers (local-only board); seats may "
                    f"read & quote any of {config.grounding.n_files} files under "
                    f"{config.grounding.repo_root}, but those bytes stay on this machine.")
        return "This run sends nothing to external providers (local-only board)."
    pretty = ", ".join(providers)
    if config.ask is not None:
        # A post-verdict follow-up (ask) is not a review — it sends a NEW question plus
        # run-context bytes to the addressed seat(s) only. Give it its own accurate
        # disclosure rather than the review-shaped base below (ask never grounds or
        # revises, so this returns here).
        a = config.ask
        seats = ", ".join(s.id for s in config.board)
        material = ("the recovered reviewed material, " if a.source_recovered_from
                    else "")
        return (f"This post-verdict follow-up sends to {pretty} ({seats}): your "
                f"question, {material}a mechanical digest of the prior verdict, and the "
                "addressed seat(s)' own prior review from that run. Proceed?")
    base = f"This review sends your source material to {pretty}."
    if config.grounding is not None:
        base += (f" Seats may also read & quote any of {config.grounding.n_files} files under "
                 f"{config.grounding.repo_root}, which can be transmitted to {pretty} and fan "
                 "out to the other seats in round 2+.")
    if config.revision is not None:
        base += (f" The round-1 prompts ALSO carry a digest of the prior run's verdict and a "
                 f"diff against the previously reviewed draft (--revise {config.revision.run_dir}), "
                 "which egress with the source.")
    return base + " Proceed?"


def unenforced_network_note(config: RunConfig) -> Optional[str]:
    """The warning to show wherever a human consents to egress. None when every
    seat is network-isolated (or in advisory mode, where grounding is intended)."""
    seats = config.unenforced_network_seats
    if not seats:
        return None
    return ("⚠ NETWORK NOT ISOLATED for: " + ", ".join(seats) + " — gate mode cannot remove "
            "these seats' network (no CLI flag disables their web/grounding tools), so a prompt "
            "injection in the source could still drive them to fetch or exfiltrate. Treat them "
            "as networked.")


def _d4_refusal_detail(seats: list) -> str:
    """The D4 hard-stop guidance: gate + --repo needs network-isolated seats, and
    these one(s) cannot be isolated. Names the offending seat(s) so the refusal is a
    labeled NO-GO (never a silent drop), and points at the three real fixes."""
    names = ", ".join(seats)
    return ("gate + --repo needs network-isolated seats; "
            f"{names} can't be isolated — drop them (e.g. --board claude,codex), "
            "add a local seat, or use --mode advisory.")


def enforce_egress_gate(config: RunConfig, blobs: list, *, assume_yes: bool,
                        skip_gate: bool, interactive: Optional[bool] = None) -> EgressApproval:
    """The pre-spawn hard stop. Returns an approval, or a refusal that callers
    MUST treat as "do not spawn". No board subprocess may run before this passes.
    """
    content_hash = packet_hash(blobs)
    stamp = now_stamp()
    scope_hash = config.grounding.scope_hash if config.grounding is not None else None

    # Every approval below binds to BOTH hashes (the prompt packet and, when grounded,
    # the repo scope a seat could read). Stamping them in one place means no path can
    # silently drop the scope binding (§8: consent covers everything that can leave).
    def decide(approved: bool, mode: str, detail: str) -> EgressApproval:
        return EgressApproval(approved, mode, content_hash, stamp, detail, scope_hash=scope_hash)

    external = [b for b in blobs if b.provider != "local"]

    # D4 (the crux) — read XOR network. A gate-bearing run with --repo REQUIRES every
    # seat to be network-isolatable: a seat that can read the repo AND reach the network
    # is the read-then-exfiltrate channel the quarantine exists to break (R2). If gate
    # mode cannot remove a seat's network (gemini/antigravity — no flag disables their
    # web/grounding), refuse the WHOLE run UNCONDITIONALLY, before any consent prompt.
    # This is a HARD-STOP, never a y/N consent question and never an auto-drop: the plan
    # rejects warning-only/proceed and auto-drop-and-proceed alike (it "launders consent
    # into false safety"). The message names the offending seat(s) so the seat is a
    # labeled NO-GO, never silently dropped. Advisory + --repo is intentionally NOT
    # blocked here (you own your repo's risk; the unenforced_network_note warns) —
    # unenforced_network_seats is empty in advisory mode, so this never fires there.
    # Gate on the REPO FLAG (config.grounded), not on whether grounding happens to be
    # populated, so a future path that leaves config.grounding=None on a grounded run
    # FAILS CLOSED here instead of falling through to approval (R: D4 keyed on
    # grounding-is-not-None). If a grounded gate run reaches the egress gate with no
    # resolved grounding, that is an internal invariant break — refuse, never approve.
    if config.gate_mode and config.grounded:
        if config.grounding is None:
            return decide(False, "refused",
                          "internal: grounded gate run reached the egress gate without resolved "
                          "repo grounding — refusing (fail-closed)")
        offending = config.unenforced_network_seats
        if offending:
            return decide(False, "refused", _d4_refusal_detail(offending))

    # local-only + --repo + an external seat: forbid explicitly. A grounded seat can
    # quote any in-scope file into its reply, which would egress to the external
    # provider — exactly what local-only forbids. Refuse with repo-specific guidance
    # BEFORE the generic local-only stop so the user knows the repo is why.
    if config.sensitivity == "local-only" and config.grounding is not None and external:
        return decide(False, "refused",
                      "sensitivity is local-only but --repo lets seats read & quote the repo to "
                      "external providers; drop --repo, use a local-only board, or raise sensitivity")

    # local-only / must-not-leave: external egress is forbidden outright.
    if config.sensitivity == "local-only" and external:
        return decide(False, "refused",
                      "sensitivity is local-only but the board has external seats; "
                      "use a local-only board or change sensitivity")

    if not external:
        return decide(True, "disclosure", "no external egress (local-only board)")

    # Every path below egresses to external providers — surface the unenforced-
    # network warning AND the repo secret-scan here, once, so they reach every consent
    # surface (public, --yes, --skip, interactive, and the non-TTY refusal) without
    # duplicating. The secret-scan is advisory (a hit may be a fixture) but the user
    # must SEE it before any grounded egress; it never echoes the full secret.
    note = unenforced_network_note(config)
    if note:
        print(note)
    if config.grounding is not None and config.grounding.secret_hits:
        print(f"⚠ repo secret-scan flagged {len(config.grounding.secret_hits)} in-scope file(s) — "
              "review the egress manifest before approving (these files are in the readable scope):")
        for rel, kind in config.grounding.secret_hits[:20]:
            print(f"    - {rel} ({kind})")

    # Public: disclosure is shown, the run proceeds (tiered consent, decision #2).
    if config.sensitivity == "public":
        return decide(True, "disclosure", "clearly-public material; proceeded after disclosure")

    # Non-public (redacted): hash-bound approval required, unless overridden.
    if skip_gate:
        return decide(True, "override",
                      "OVERRIDE: --skip-sensitivity-gate bypassed hash-bound approval")
    if assume_yes:
        return decide(True, "hash-bound", "approved via --yes (bound to the content+scope hash)"
                      if scope_hash else "approved via --yes (bound to the content hash)")

    is_tty = interactive if interactive is not None else sys.stdin.isatty()
    if not is_tty:
        return decide(False, "refused",
                      "non-public material requires approval; re-run with --yes "
                      "or interactively, or mark the source --sensitivity public")

    print(disclosure_line(config))
    print(f"Packet content hash (sha256): {content_hash}")
    if scope_hash is not None:
        g = config.grounding
        print(f"Repo scope hash (sha256): {scope_hash}  "
              f"({g.n_files} file(s), {g.n_bytes} bytes under {g.repo_root})")
        prompt = "Approve egress of this exact packet AND repo scope? [y/N] "
        ok_detail = "approved interactively (bound to the content+scope hash)"
    else:
        prompt = "Approve egress of this exact packet? [y/N] "
        ok_detail = "approved interactively (bound to the content hash)"
    answer = input(prompt).strip().lower()
    if answer in ("y", "yes"):
        return decide(True, "hash-bound", ok_detail)
    return decide(False, "refused", "approval declined")
