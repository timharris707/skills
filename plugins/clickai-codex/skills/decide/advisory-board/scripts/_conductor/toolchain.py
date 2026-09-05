"""Toolchain currency (design §7a): check each seat CLI vs its latest release,
update stale CLIs / install missing ones on consent, and propose a fallback
model id when a pinned id 404s."""
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

from _conductor.constants import SMOKE_PROMPT
from _conductor.registry import (
    SeatAdapter,
    model_not_found,
    parse_semver,
    version_is_current,
)
from _conductor.config import SeatConfig
from _conductor.spawn import (
    classify,
    spawn,
)

__all__ = [
    "ToolStatus",
    "check_tool",
    "check_toolchain",
    "_tool_status_label",
    "render_toolchain_table",
    "update_tool",
    "update_stale_tools",
    "install_tool",
    "install_missing_tools",
    "propose_model",
]


@dataclass
class ToolStatus:
    seat: str
    pkg_label: str
    installed: Optional[str]
    latest: Optional[str]
    current: Optional[bool]        # True up-to-date, False stale, None can't judge
    update_argv: Optional[list]    # set only when stale and an updater is known
    note: str = ""                 # advisories (manager missing, flag-drift) — never fatal
    present: bool = True           # is the CLI binary installed at all? (False => "missing")
    install_argv: Optional[list] = None  # how to install it when absent
    auth_hint: str = ""            # how to authenticate after install


def check_tool(adapter: SeatAdapter) -> ToolStatus:
    """Read installed vs latest version for one seat. Read-only, never updates."""
    iv = spawn(adapter, adapter.version_argv(), timeout=15)
    # exit 127 == binary not found (spawn maps FileNotFoundError -> 127). Distinguish
    # "not installed" (offer to install) from "installed but version unreadable".
    present = iv.exit_code != 127
    install = adapter.install_argv() if adapter.install_argv else None
    if not present:
        # note stays empty — the "missing" status + the install section already say it.
        return ToolStatus(adapter.name, adapter.pkg_label or adapter.provider,
                          None, None, None, None, "",
                          present=False, install_argv=install, auth_hint=adapter.auth_hint)
    installed = parse_semver(iv.stdout + "\n" + iv.stderr) if iv.exit_code == 0 else None

    latest, note = None, ""
    if adapter.latest_argv and adapter.parse_latest:
        res = spawn(adapter, adapter.latest_argv(), timeout=45)
        if res.exit_code == 0:
            latest = adapter.parse_latest(res.stdout)
        if latest is None:
            mgr = adapter.latest_argv()[0]
            note = f"latest unknown ({mgr} unavailable or unparsable)"

    current = version_is_current(installed, latest)

    # Flag-drift advisory: build_argv's flags were grounded against a specific CLI
    # version. If the installed CLI is newer, the flags may have moved — surface it
    # (this is the "re-verify after an 8-version jump" reminder, made automatic).
    if installed and adapter.flags_verified_version:
        if version_is_current(adapter.flags_verified_version, installed) is False:
            drift = f"flags grounded at {adapter.flags_verified_version}, now {installed} — re-verify --help"
            note = f"{note}; {drift}" if note else drift

    upd = adapter.update_argv() if (adapter.update_argv and current is False) else None
    return ToolStatus(adapter.name, adapter.pkg_label or adapter.provider,
                      installed, latest, current, upd, note,
                      present=True, install_argv=None, auth_hint=adapter.auth_hint)


def check_toolchain(adapters: list) -> list:
    return [check_tool(a) for a in adapters]


def _tool_status_label(s: ToolStatus) -> str:
    if not s.present:
        return "missing"
    return "current" if s.current else ("STALE" if s.current is False else "unknown")


def render_toolchain_table(statuses: list) -> str:
    rows = ["| Seat        | Manager                       | Installed | Latest  | Status  |",
            "| ----------- | ----------------------------- | --------- | ------- | ------- |"]
    for s in statuses:
        rows.append(f"| {s.seat:<11} | {s.pkg_label:<29} | {(s.installed or '—'):<9} "
                    f"| {(s.latest or '?'):<7} | {_tool_status_label(s):<7} |")
    stale = [s for s in statuses if s.current is False and s.present]
    missing = [s for s in statuses if not s.present]
    rows.append("")
    if stale:
        rows.append(f"{len(stale)} of {len(statuses)} CLIs behind latest: "
                    + ", ".join(f"{s.seat} ({s.installed}→{s.latest})" for s in stale))
        rows.append("update with:  run_board.py toolchain --update")
    elif not missing:
        rows.append(f"all {len(statuses)} CLIs current (or unknown).")
    # Not-installed seats: print the exact install command (guidance by default).
    if missing:
        rows.append("")
        rows.append(f"{len(missing)} seat CLI(s) not installed:")
        for s in missing:
            cmd = " ".join(s.install_argv) if s.install_argv else "(no installer known)"
            rows.append(f"  {s.seat:<11} install: {cmd}")
            if s.auth_hint:
                rows.append(f"  {'':<11} then:    {s.auth_hint}")
        rows.append("install with:  run_board.py toolchain --install   "
                    "(note: installing a CLI does NOT grant an account — you still need provider auth)")
    for s in statuses:
        if s.note:
            rows.append(f"  note ({s.seat}): {s.note}")
    return "\n".join(rows)


def update_tool(status: ToolStatus) -> tuple:
    """Run one seat's updater, streaming its output. Returns (ok, detail)."""
    if not status.update_argv:
        return True, "nothing to update"
    print(f"  updating {status.seat} ({status.pkg_label}) "
          f"{status.installed} → {status.latest} ...")
    try:
        completed = subprocess.run(status.update_argv)
    except FileNotFoundError:
        return False, f"updater not found: {status.update_argv[0]}"
    ok = completed.returncode == 0
    return ok, ("updated" if ok else f"update failed (exit {completed.returncode})")


def update_stale_tools(statuses: list, *, assume_yes: bool,
                       interactive: Optional[bool] = None) -> int:
    """Consent-gated update of every stale seat (design decision: detect+confirm).

    Mirrors the egress gate's consent posture: --yes approves unattended; an
    interactive TTY is prompted y/N; a non-TTY without --yes is a no-op (it tells
    you to re-run with --yes) rather than a hard error. Returns the count of
    updates that FAILED (0 == all good / nothing to do / declined).
    """
    stale = [s for s in statuses if s.current is False and s.update_argv]
    if not stale:
        return 0
    if not assume_yes:
        is_tty = interactive if interactive is not None else sys.stdin.isatty()
        if not is_tty:
            print("stale CLIs found; re-run with --yes (or interactively) to update them.")
            return 0
        reply = input(f"\nUpdate {len(stale)} stale CLI(s)? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("no update performed.")
            return 0
    failed = 0
    for s in stale:
        ok, detail = update_tool(s)
        print(f"  {s.seat}: {detail}")
        failed += 0 if ok else 1
    return failed


def install_tool(status: ToolStatus) -> tuple:
    """Install one absent seat CLI, streaming its output. Returns (ok, detail)."""
    if not status.install_argv:
        return True, "no installer known"
    print(f"  installing {status.seat} ({status.pkg_label}): "
          f"{' '.join(status.install_argv)} ...")
    try:
        completed = subprocess.run(status.install_argv)
    except FileNotFoundError:
        return False, f"installer not found: {status.install_argv[0]}"
    ok = completed.returncode == 0
    return ok, ("installed" if ok else f"install failed (exit {completed.returncode})")


def install_missing_tools(statuses: list, *, assume_yes: bool,
                          interactive: Optional[bool] = None) -> int:
    """Consent-gated install of absent seat CLIs (same posture as update). Note: a
    successful install still does not grant a provider account — auth is separate.
    Returns the count of installs that FAILED (0 == all good / nothing to do / declined)."""
    missing = [s for s in statuses if not s.present and s.install_argv]
    if not missing:
        return 0
    if not assume_yes:
        is_tty = interactive if interactive is not None else sys.stdin.isatty()
        if not is_tty:
            print("missing CLIs found; re-run with --yes (or interactively) to install them.")
            return 0
        reply = input(f"\nInstall {len(missing)} missing CLI(s)? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("no install performed.")
            return 0
    failed = 0
    for s in missing:
        ok, detail = install_tool(s)
        print(f"  {s.seat}: {detail}"
              + ("  (now authenticate — install ≠ account)" if ok else ""))
        failed += 0 if ok else 1
    return failed


def propose_model(seat: SeatConfig, *, network_on: bool, workdir: Optional[str],
                  smoke_timeout: int = 45) -> Optional[str]:
    """When a seat's pinned model 404s, probe its fallbacks and return the first
    that resolves — a PROPOSAL for the user, never an automatic swap (model ids
    stay pinned per the advisory-board-model-policy)."""
    adapter = seat.adapter
    for candidate in adapter.fallback_models:
        if candidate == seat.model:
            continue
        argv = adapter.build_argv(candidate, SMOKE_PROMPT, reasoning=seat.reasoning,
                                  workdir=workdir, network=network_on)
        smoke = spawn(adapter, argv, prompt=SMOKE_PROMPT, timeout=smoke_timeout, cwd=workdir)
        status, _ = classify(smoke, adapter)
        # include_stdout: smoke-ping path (fixed SMOKE_PROMPT) where claude emits its
        # genuine model-not-found notice to stdout — same rationale as preflight_seat.
        if status in ("ran", "degraded") and not model_not_found(smoke, include_stdout=True):
            return candidate
    return None
