#!/usr/bin/env python3
"""Render the 14-feature scoreboard (design/feature-tracker.html) FROM the
roadmap markdown — the plan file stays the single source of truth (D1); this
view derives every status from its checkboxes and PR tags, exactly like
render_plan.py derives the full plan view. Regenerate whenever the plan
changes; never hand-edit the HTML.

Usage:
  python3 skills/advisory-board/scripts/render_tracker.py design/run-board-roadmap-v1.11-v1.15.md
  (writes design/feature-tracker.html next to the plan)

Stdlib only. Deterministic: the only date shown is the plan's own Updated: line.
"""
from __future__ import annotations

import html
import os
import re
import sys

# The ranked slate (fixed since the 2026-07-01 review): display names per tag.
# Status/PRs are NEVER stored here — they derive from the plan's checkboxes.
# "6" is the one slate item the plan tags by milestone rather than number:
# rubric-first deliberation, the whole of v1.15.
FEATURES = [
    ("1",  "--revise — re-review a revised draft with a verdict delta"),
    ("2",  "Revised-draft transform — the board hands back a fixed copy + changes.json"),
    ("3a", "Cost/time capture + preflight estimate"),
    ("3b", "--tier quick|standard|deep run presets"),
    ("4",  "ask — post-verdict cross-examination of a seat"),
    ("5",  "Persistent runs root + history"),
    ("6",  "Rubric-first deliberation (design-first)"),
    ("7",  "Setup doctor — provider sweep + fix-it steps"),
    ("8",  "Severity filters (--filter / --min-severity)"),
    ("9",  "Independence / echo score"),
    ("10", "Live progress view"),
    ("11", "Amendments — human-owned verdict tuning (amend)"),
    ("12", "Inline citation snippets in the handoff"),
    ("13", "Structured digest as typed JSON (--digest-format json)"),
    ("14", "Per-seat --timeout"),
]

MILESTONE_RE = re.compile(r"^## Milestone: (v[\d.]+) — (.+)$")
PHASE_RE = re.compile(r"^### Phase \d+ — (.+?)(?:\s*\(([^)]*#[^)]*)\))?\s*$")
BOX_RE = re.compile(r"^- \[([ x])\] ")
TAG_RE = re.compile(r"#(\d+[ab]?)\b")
PR_RE = re.compile(r"PR #(\d+)")
UPDATED_RE = re.compile(r"^- \*\*Updated:\*\* (.+)$")
STATUS_RE = re.compile(r"^- \*\*Status:\*\* (.+)$")

REPO_PR_URL = "https://github.com/timharris707/skills/pull/{n}"


def parse_plan(text: str) -> dict:
    """Milestones -> phases (title, tags, boxes done/total, PR numbers)."""
    plan = {"milestones": [], "updated": "", "status": ""}
    milestone = None
    phase = None
    for line in text.splitlines():
        m = UPDATED_RE.match(line)
        if m:
            plan["updated"] = m.group(1).strip()
        m = STATUS_RE.match(line)
        if m:
            plan["status"] = m.group(1).strip()
        m = MILESTONE_RE.match(line)
        if m:
            milestone = {"version": m.group(1), "title": m.group(2).strip(), "phases": []}
            plan["milestones"].append(milestone)
            phase = None
            continue
        if line.startswith("## "):        # Decisions / Risks / Later etc. end the milestones
            milestone = None
            phase = None
            continue
        if milestone is None:
            continue
        m = PHASE_RE.match(line)
        if m:
            tags = TAG_RE.findall(m.group(2) or "")
            phase = {"title": m.group(1).strip(), "tags": tags,
                     "done": 0, "total": 0, "prs": []}
            milestone["phases"].append(phase)
            continue
        if phase is not None:
            m = BOX_RE.match(line)
            if m:
                phase["total"] += 1
                if m.group(1) == "x":
                    phase["done"] += 1
                phase["prs"] += [int(n) for n in PR_RE.findall(line)]
    return plan


def _is_release_phase(phase: dict) -> bool:
    return "release" in phase["title"].lower()


def feature_rows(plan: dict) -> list:
    """One row per slate feature, status derived from its phases' checkboxes."""
    by_tag = {}
    for milestone in plan["milestones"]:
        for phase in milestone["phases"]:
            for tag in phase["tags"]:
                by_tag.setdefault(tag, []).append((milestone, phase))
    rows = []
    for tag, name in FEATURES:
        if tag == "6":   # rubric-first: the whole of v1.15, untagged in the plan
            phases = [(m, p) for m in plan["milestones"] if m["version"] == "v1.15"
                      for p in m["phases"] if not _is_release_phase(p)]
        else:
            phases = by_tag.get(tag, [])
        if not phases:
            rows.append({"tag": tag, "name": name, "version": "?",
                         "state": "pending", "done": 0, "total": 0, "prs": []})
            continue
        version = phases[0][0]["version"]
        done = sum(p["done"] for _, p in phases)
        total = sum(p["total"] for _, p in phases)
        prs = sorted({n for _, p in phases for n in p["prs"]})
        state = ("shipped" if total and done == total
                 else "inprogress" if done else "pending")
        rows.append({"tag": tag, "name": name, "version": version,
                     "state": state, "done": done, "total": total, "prs": prs})
    return rows


def release_rows(plan: dict) -> list:
    rows = []
    for milestone in plan["milestones"]:
        release_phases = [p for p in milestone["phases"] if _is_release_phase(p)]
        feature_phases = [p for p in milestone["phases"] if not _is_release_phase(p)]
        f_done = sum(p["done"] for p in feature_phases)
        f_total = sum(p["total"] for p in feature_phases)
        r_done = sum(p["done"] for p in release_phases)
        r_total = sum(p["total"] for p in release_phases)
        if r_total and r_done == r_total:
            state = "released"
        elif f_total and f_done == f_total:
            state = "gate"       # features done; release awaits the explicit go
        elif f_done:
            state = "inprogress"
        else:
            state = "pending"
        rows.append({"version": milestone["version"], "title": milestone["title"],
                     "state": state, "done": f_done, "total": f_total})
    return rows


_STATE_LABEL = {
    "shipped": "SHIPPED", "inprogress": "IN PROGRESS", "pending": "PENDING",
    "released": "RELEASED", "gate": "AT RELEASE GATE",
}


def _pr_links(prs: list) -> str:
    return ", ".join(f'<a href="{REPO_PR_URL.format(n=n)}">#{n}</a>' for n in prs)


def render_html(plan: dict) -> str:
    rows = feature_rows(plan)
    shipped = sum(1 for r in rows if r["state"] == "shipped")
    pct = round(100 * shipped / len(rows)) if rows else 0
    feature_html = []
    for r in rows:
        label = _STATE_LABEL[r["state"]]
        if r["state"] == "inprogress":
            label += f" ({r['done']}/{r['total']})"
        feature_html.append(
            f'<tr class="{r["state"]}"><td class="num">#{html.escape(r["tag"])}</td>'
            f'<td>{html.escape(r["name"])}</td>'
            f'<td class="ver">{html.escape(r["version"])}</td>'
            f'<td><span class="pill {r["state"]}">{label}</span></td>'
            f'<td class="prs">{_pr_links(r["prs"])}</td></tr>')
    release_html = []
    for r in release_rows(plan):
        frac = f'{r["done"]}/{r["total"]}' if r["total"] else "—"
        release_html.append(
            f'<tr class="{r["state"]}"><td class="ver">{html.escape(r["version"])}</td>'
            f'<td>{html.escape(r["title"])}</td><td class="num">{frac}</td>'
            f'<td><span class="pill {r["state"]}">{_STATE_LABEL[r["state"]]}</span></td></tr>')
    updated = html.escape(plan["updated"] or "?")
    status = html.escape(plan["status"] or "")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Advisory Board — Feature Tracker (v1.11 → v1.15)</title>
<style>
  :root {{
    --bg: #0f1216; --card: #161b22; --ink: #e6edf3; --faint: #8b95a7;
    --line: #2b3240; --ok: #3fb950; --ok-bg: rgba(63,185,80,.12);
    --warn: #d29922; --warn-bg: rgba(210,153,34,.12);
    --idle: #8b95a7; --idle-bg: rgba(139,149,167,.10);
    --gate: #58a6ff; --gate-bg: rgba(88,166,255,.12);
  }}
  @media (prefers-color-scheme: light) {{
    :root {{ --bg:#f6f8fa; --card:#ffffff; --ink:#1f2328; --faint:#59636e;
             --line:#d1d9e0; }}
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 32px 20px 60px; background: var(--bg); color: var(--ink);
          font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
  .wrap {{ max-width: 940px; margin: 0 auto; }}
  h1 {{ font-size: 21px; margin: 0 0 4px; }}
  .sub {{ color: var(--faint); font-size: 13.5px; margin: 0 0 22px; }}
  .bar {{ height: 10px; border-radius: 999px; background: var(--line);
          overflow: hidden; margin: 14px 0 6px; }}
  .bar > div {{ height: 100%; width: {pct}%; background: var(--ok); }}
  .barlab {{ font-size: 13px; color: var(--faint); margin-bottom: 26px; }}
  h2 {{ font-size: 13px; letter-spacing: .08em; text-transform: uppercase;
        color: var(--faint); margin: 34px 0 10px; }}
  table {{ width: 100%; border-collapse: collapse; background: var(--card);
           border: 1px solid var(--line); border-radius: 10px; overflow: hidden; }}
  th, td {{ text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--line);
            font-size: 14px; vertical-align: top; }}
  th {{ font-size: 12px; letter-spacing: .06em; text-transform: uppercase;
        color: var(--faint); background: transparent; }}
  tr:last-child td {{ border-bottom: none; }}
  td.num {{ color: var(--faint); white-space: nowrap; width: 46px; }}
  td.ver {{ white-space: nowrap; width: 58px; color: var(--faint); }}
  td.prs {{ white-space: nowrap; }}
  td.prs a {{ color: var(--gate); text-decoration: none; }}
  .pill {{ display: inline-block; font-size: 11px; font-weight: 700;
           letter-spacing: .05em; padding: 2px 9px; border-radius: 999px;
           white-space: nowrap; }}
  .pill.shipped, .pill.released {{ color: var(--ok); background: var(--ok-bg); }}
  .pill.inprogress {{ color: var(--warn); background: var(--warn-bg); }}
  .pill.pending {{ color: var(--idle); background: var(--idle-bg); }}
  .pill.gate {{ color: var(--gate); background: var(--gate-bg); }}
  tr.shipped td, tr.released td {{ opacity: .92; }}
  .foot {{ margin-top: 26px; color: var(--faint); font-size: 12.5px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>Advisory Board — Feature Tracker</h1>
  <p class="sub">Fourteen features across five releases · derived from the roadmap
  (<code>design/run-board-roadmap-v1.11-v1.15.md</code>) — the markdown is the source of
  truth; regenerate with <code>render_tracker.py</code>, never hand-edit.<br>
  Plan updated: {updated}{" · " + status if status else ""}</p>

  <div class="bar"><div></div></div>
  <div class="barlab">{shipped} of {len(rows)} slate items shipped ({pct}%) — fourteen
  features; #3 ships as 3a + 3b</div>

  <h2>Features (the ranked slate)</h2>
  <table>
    <tr><th>#</th><th>Feature</th><th>Release</th><th>Status</th><th>PRs</th></tr>
    {''.join(feature_html)}
  </table>

  <h2>Releases</h2>
  <table>
    <tr><th>Tag</th><th>Milestone</th><th>Feature boxes</th><th>Status</th></tr>
    {''.join(release_html)}
  </table>

  <p class="foot">Status derives from the plan's checkboxes: a feature is SHIPPED when
  every checkbox of its phase(s) is ticked (work in flight shows as PENDING until its
  PR merges and the plan is ticked). Releases wait for Tim's explicit go at each gate.</p>
</div>
</body>
</html>
"""


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        print("usage: render_tracker.py <roadmap.md>", file=sys.stderr)
        return 2
    plan_path = argv[0]
    with open(plan_path, encoding="utf-8") as handle:
        plan = parse_plan(handle.read())
    out_path = os.path.join(os.path.dirname(plan_path) or ".", "feature-tracker.html")
    text = render_html(plan)
    with open(out_path, "w", encoding="utf-8") as handle:
        handle.write(text)
    print(f"wrote {out_path} ({len(text.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
