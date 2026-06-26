#!/usr/bin/env python3
"""Render an advisory-board verdict.json into a shareable format.

Usage:
  format_output.py verdict.json --format tldr|pr|slack|json

Reads the verdict.json described in references/verdict-schema.md and writes the
chosen format to stdout. Deterministic - no model call. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _verdict_labels import human_label, is_software_lens, lens_disclaimer  # noqa: E402  lens-aware label + disclaimer


def die(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        die(f"{path}: not found")
    except json.JSONDecodeError as exc:
        die(f"{path}: invalid JSON ({exc})")
    if "verdict" not in data:
        die(f"{path}: missing required field 'verdict'")
    return data


def verdict_line(data: dict) -> str:
    stance = "unanimous" if data.get("unanimous") else "split board"
    lens_preset = data.get("lens_preset")
    label, _ = human_label(data.get("verdict"), lens_preset, data.get("decision"))
    # Software labels (and a native decision) read as upper-case tokens, as they
    # always have; plain-language labels keep their natural case so "Stop and rethink"
    # doesn't become a shouted "STOP AND RETHINK".
    if data.get("decision") or is_software_lens(lens_preset):
        label = label.upper()
    return f"{label} ({data.get('confidence', '?')} confidence, {stance})"


def _disclaimer(data: dict):
    """The lens-aware professional-advice caveat, or None for a software/absent lens."""
    return lens_disclaimer(data.get("lens_preset"))


def as_tldr(data: dict) -> str:
    blockers = data.get("blockers", [])
    tops = "; ".join(b.get("title", "blocker") for b in blockers[:3]) if blockers else ""
    title = data.get("title", "Review")
    tail = f" Top blockers: {tops}." if blockers else ""
    disclaimer = _disclaimer(data)
    note = f" ({disclaimer})" if disclaimer else ""
    return f"{title}: {verdict_line(data)}.{tail}{note}"


def as_pr(data: dict) -> str:
    out = [f"## Advisory board: {verdict_line(data)}", ""]
    if data.get("title"):
        out += [f"_{data['title']}_", ""]
    blockers = data.get("blockers", [])
    if blockers:
        out.append("### Blockers")
        for b in blockers:
            body = f" - {b['body']}" if b.get("body") else ""
            out.append(f"- [ ] **{b.get('title', 'blocker')}**{body}")
        out.append("")
    dissent = data.get("dissent", [])
    if dissent:
        out.append("### Dissent")
        for d in dissent:
            out.append(f"- _{d.get('who', '-')}:_ {d.get('body', '')}")
        out.append("")
    actions = data.get("next_actions", [])
    if actions:
        out.append("### Next actions")
        out += [f"1. {a}" for a in actions]
        out.append("")
    seats = ", ".join(f"{s.get('seat', '?')} ({s.get('model', '?')})" for s in data.get("board", []))
    rounds = data.get("rounds", "?")
    plural = "" if rounds == 1 else "s"
    out.append(f"<sub>Board: {seats} - {rounds} round{plural}.</sub>")
    disclaimer = _disclaimer(data)
    if disclaimer:
        out += ["", f"<sub>_{disclaimer}_</sub>"]
    return "\n".join(out)


def as_slack(data: dict) -> str:
    out = [f"*Advisory board: {verdict_line(data)}*"]
    if data.get("title"):
        out.append(f"_{data['title']}_")
    blockers = data.get("blockers", [])
    if blockers:
        out.append("*Blockers:*")
        out += [f"• {b.get('title', 'blocker')}" for b in blockers]
    actions = data.get("next_actions", [])
    if actions:
        out.append("*Next:* " + "; ".join(actions))
    disclaimer = _disclaimer(data)
    if disclaimer:
        out.append(f"_{disclaimer}_")
    return "\n".join(out)


RENDERERS = {"tldr": as_tldr, "pr": as_pr, "slack": as_slack}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Render verdict.json into a shareable format.")
    parser.add_argument("path", nargs="?", default="verdict.json")
    parser.add_argument("--format", choices=("tldr", "pr", "slack", "json"), default="tldr")
    args = parser.parse_args(argv)

    data = load(args.path)
    if args.format == "json":
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 0
    print(RENDERERS[args.format](data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
