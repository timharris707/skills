"""The seat-adapter registry (design §6) — the single place that knows each
CLI's quirks: argv builders, version/update/install argv, the model-answered
and model-not-found parsers, semver helpers, and the REGISTRY itself."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable, Optional

__all__ = [
    "SeatAdapter",
    "_model_answered_none",
    "_MODEL_JSON_RE",
    "_MODEL_BANNER_RE",
    "parse_model_answered",
    "claude_argv",
    "claude_version",
    "codex_argv",
    "codex_version",
    "gemini_argv",
    "gemini_version",
    "antigravity_argv",
    "antigravity_version",
    "ollama_argv",
    "ollama_version",
    "claude_latest_argv",
    "claude_update_argv",
    "claude_install_argv",
    "codex_latest_argv",
    "codex_update_argv",
    "codex_install_argv",
    "gemini_latest_argv",
    "gemini_update_argv",
    "gemini_install_argv",
    "antigravity_latest_argv",
    "antigravity_update_argv",
    "antigravity_install_argv",
    "ollama_latest_argv",
    "ollama_update_argv",
    "ollama_install_argv",
    "_SEMVER_RE",
    "parse_semver",
    "parse_npm_latest",
    "parse_brew_latest",
    "parse_brew_cask_latest",
    "version_tuple",
    "version_is_current",
    "_MODEL_NOT_FOUND_SIGNALS",
    "model_not_found",
    "REGISTRY",
]


# Seat-adapter registry (design §6) — the only place that knows a CLI's quirks.
#
# Each adapter's build_argv produces the exact argv for a seat. The gate-mode
# isolation flags live HERE, in code, where they are testable:
#   * stdin handling (codex must run with stdin closed or `codex exec` hangs);
#   * read-only enforcement (claude plan mode / codex read-only sandbox /
#     gemini approval-mode plan);
#   * network removal for gate mode (claude --disallowed-tools WebSearch/WebFetch;
#     codex read-only sandbox already has no network, plus --ephemeral so no
#     session files are written; gemini plan mode executes no tools).
#
# CLI drift (a renamed flag, gpt-5.5 -> gpt-5.6) is a one-line edit here, never a
# six-file hunt. Flags were grounded against the installed CLIs' --help on
# 2026-06-25; re-verify before a large run, they move fast.


@dataclass(frozen=True)
class SeatAdapter:
    name: str
    default_model: str
    provider: str
    default_reasoning: str
    build_argv: Callable[..., list]      # (model, prompt, *, reasoning, workdir, network) -> argv
    version_argv: Callable[[], list]     # () -> argv for the binary-present check
    prompt_on_stdin: bool                # True: feed prompt via stdin; False: it is in argv
    close_stdin: bool                    # True: stdin=DEVNULL when not feeding a prompt (codex hang fix)
    stderr_is_fatal: bool                # False for Gemini (router noise on stderr is normal); consumed at M3 fan-out
    supports_isolation: bool             # can this CLI run scoped-dir in gate mode (via -C or cwd)?
    isolates_network: bool               # can gate mode actually REMOVE this seat's network via a flag?
    model_answered: Callable[[str, str], Optional[str]]  # (stdout, stderr) -> real model id | None
    timeout_s: int = 900                 # hard cap; §13 default is 15 min (overridden per call)
    # --- toolchain currency + model self-heal (all optional; a seat without a
    #     package manager simply reports "unknown" and is never auto-updated) ---
    latest_argv: Optional[Callable[[], list]] = None     # () -> argv that prints the latest version
    parse_latest: Optional[Callable[[str], Optional[str]]] = None  # stdout -> version str
    update_argv: Optional[Callable[[], list]] = None     # () -> argv that updates this CLI
    install_argv: Optional[Callable[[], list]] = None    # () -> argv that installs this CLI when absent
    auth_hint: str = ""                  # how to authenticate after install (no secrets)
    pkg_label: str = ""                  # human label for the manager, e.g. "brew gemini-cli"
    flags_verified_version: str = ""     # CLI version build_argv's flags were last grounded against
    fallback_models: tuple = ()          # ordered ids to PROBE + PROPOSE if default_model 404s
                                         # (never auto-applied — model ids stay pinned per policy)


def _model_answered_none(stdout: str, stderr: str) -> Optional[str]:
    """Deliberately-unknown model-answered parser.

    Returns None ("unknown — flag it"), never "assume the requested model
    answered". Used where the CLI cannot report the answering model reliably:
    antigravity silently SUBSTITUTES an unknown model id (rc 0, no banner), so the
    requested model can never be trusted to have answered (design §16, handoff
    GOTCHA). The honest provenance is "unknown", surfaced as such everywhere.
    """
    return None


# Best-effort "which model actually answered" parser (design §12 provenance, §16
# "a model_answered miss is 'unknown — flag it', never assume requested"). We scan
# ONLY stderr: the review prose on stdout routinely contains the word "model" and
# must never be mined for a false id. Most CLIs do not print the answering model in
# plain text, so None is the common, honest v1 outcome — never a fabricated id.
_MODEL_JSON_RE = re.compile(r'"model"\s*:\s*"([^"]+)"')
_MODEL_BANNER_RE = re.compile(
    r'^\s*(?:using\s+model|model)\s*[:=]\s*["\']?([A-Za-z0-9][\w.\-/()]*(?: [\w.\-/()]+)*?)["\']?\s*$',
    re.IGNORECASE | re.MULTILINE,
)


def parse_model_answered(stdout: str, stderr: str) -> Optional[str]:
    """Return the model id a CLI *reports* having used (from stderr), or None."""
    m = _MODEL_JSON_RE.search(stderr) or _MODEL_BANNER_RE.search(stderr)
    if not m:
        return None
    cand = m.group(1).strip()
    return cand or None


# v1 is always read-only — every adapter hardcodes its provider's read-only mode
# below (claude plan / codex read-only sandbox / gemini approval-mode plan). There
# is intentionally no `read_only` parameter: an edit-capable seat is out of scope
# until M3+, and a silently-ignored flag is a worse footgun than its absence.


def claude_argv(model, prompt, *, reasoning="xhigh", workdir=None, network=False):
    # claude -p reads the prompt from stdin; plan mode is read-only. fs scoping is
    # the subprocess cwd (applied at spawn), since claude has no dir-scoping flag.
    argv = ["claude", "-p", "--model", model, "--permission-mode", "plan"]
    if not network:
        # Cut the seat's network reach in gate mode. Note: NOT --bare, which would
        # force ANTHROPIC_API_KEY auth and break subscription/OAuth login.
        argv += ["--disallowed-tools", "WebSearch", "WebFetch"]
    return argv


def claude_version():
    return ["claude", "--version"]


def codex_argv(model, prompt, *, reasoning="xhigh", workdir=None, network=False):
    argv = ["codex", "exec", "--sandbox", "read-only", "--skip-git-repo-check",
            "--config", f"model={model}",
            "--config", f"model_reasoning_effort={reasoning}"]
    if not network:
        # read-only sandbox already has no network and no disk writes; --ephemeral
        # also keeps the run from persisting session files to disk.
        argv += ["--ephemeral"]
    if workdir:
        argv += ["-C", workdir]   # scoped working directory (gate mode)
    argv += [prompt]  # codex takes the prompt as a positional arg (stdin stays closed)
    return argv


def codex_version():
    return ["codex", "--version"]


def gemini_argv(model, prompt, *, reasoning="HIGH", workdir=None, network=False):
    # approval-mode plan is read-only (no edit/exec tools). HONEST LIMITATION:
    # the installed gemini CLI exposes no flag that reliably disables the built-in
    # GoogleSearch grounding, so gate mode CANNOT remove this seat's network (see
    # isolates_network=False below). fs scoping is the subprocess cwd at spawn.
    # `network`/`workdir` are accepted for a uniform signature but not enforceable
    # here — do not pretend otherwise in the consent surface.
    #
    # --skip-trust: gemini-cli >= 0.46 added "trusted folders" — headless runs in
    # an untrusted dir get approval-mode forced to default and exit 55 with NO
    # output (verified on 0.46.0). We run read-only (plan) in a scoped throwaway
    # dir, so trusting that session is safe and required for the board to work.
    return ["gemini", "-p", prompt, "-m", model, "--approval-mode", "plan", "--skip-trust"]


def gemini_version():
    return ["gemini", "--version"]


def antigravity_argv(model, prompt, *, reasoning="High", workdir=None, network=False):
    # Antigravity CLI (`agy`) is Google's agent-first successor to gemini-cli
    # (gemini-cli sunset for consumer tiers 2026-06-18). `-p` runs a single prompt
    # non-interactively and prints the response. --sandbox enables terminal
    # restrictions for a read-only-ish posture; fs scoping is the subprocess cwd.
    #
    # Two verified gotchas (grounded on agy 1.0.12, 2026-06-25):
    #  * stdin is read to EOF — without close_stdin/DEVNULL the call HANGS (codex-style).
    #  * an unknown --model is SILENTLY substituted (no error, no 404), so pin an exact
    #    display name from `agy models` ("Gemini 3.5 Flash (High)") and never trust that
    #    the requested model answered without a model_answered check (fallback probing is
    #    pointless here — it never fails loudly).
    # Effort is baked into the model display name ("... (High)"), so `reasoning` is not
    # a separate flag. Like gemini, this is an agentic harness whose web/grounding is
    # not removable, mirrored honestly as isolates_network=False.
    return ["agy", "-p", prompt, "--model", model, "--sandbox"]


def antigravity_version():
    return ["agy", "--version"]


def ollama_argv(model, prompt, *, reasoning="default", workdir=None, network=False):
    # Ollama runs the model entirely on-machine, so there is NO external egress —
    # which is exactly why a local seat is the privacy lever for sensitive material
    # (references/data-handling.md), reflected as provider="local" + isolates_network=True.
    # `ollama run <model>` reads the prompt on STDIN to EOF, prints the completion,
    # and exits (the non-interactive form; a piped stdin suppresses the REPL). The
    # prompt rides stdin (prompt_on_stdin=True), so it never lands in argv and never
    # needs shell-escaping.
    #
    # `network`/`workdir`/`reasoning` are accepted for a uniform adapter signature but
    # are NOT flags here: a local model has no web/grounding tools to remove (network
    # isolation is intrinsic), no dir-scoping flag (fs scoping is the subprocess cwd at
    # spawn), and no reasoning-effort knob.
    #
    # NOTE: grounded against Ollama's documented/stable CLI, NOT a live local install
    # (ollama was absent on the dev box). The `ollama run <model>` stdin form has been
    # stable across releases; flags_verified_version is left empty (no live grounding to
    # claim) — re-verify `ollama run --help` before a large run.
    return ["ollama", "run", model]


def ollama_version():
    return ["ollama", "--version"]


# Toolchain currency (design §7a). Each seat CLI is installed by a different
# package manager, so "what is the latest version" and "update it" live here,
# per seat, next to that CLI's other quirks. The whole point is self-healing: a
# stale CLI is the single most common reason a freshly-renamed frontier model id
# (gemini-3-flash-preview -> gemini-3.5-flash) suddenly 404s. Grounded against
# the installed managers on 2026-06-25: npm for claude/codex, Homebrew for gemini
# (formula), antigravity (cask), and ollama (formula).

def claude_latest_argv():  return ["npm", "view", "@anthropic-ai/claude-code", "version"]
def claude_update_argv():  return ["claude", "update"]
def claude_install_argv(): return ["npm", "install", "-g", "@anthropic-ai/claude-code"]

def codex_latest_argv():   return ["npm", "view", "@openai/codex", "version"]
def codex_update_argv():   return ["codex", "update"]
def codex_install_argv():  return ["npm", "install", "-g", "@openai/codex"]

def gemini_latest_argv():  return ["brew", "info", "--json=v2", "gemini-cli"]
def gemini_update_argv():  return ["brew", "upgrade", "gemini-cli"]
def gemini_install_argv(): return ["brew", "install", "gemini-cli"]

def antigravity_latest_argv():  return ["brew", "info", "--json=v2", "--cask", "antigravity-cli"]
def antigravity_update_argv():  return ["brew", "upgrade", "--cask", "antigravity-cli"]
def antigravity_install_argv(): return ["brew", "install", "--cask", "antigravity-cli"]

def ollama_latest_argv():  return ["brew", "info", "--json=v2", "ollama"]   # ships as a brew formula
def ollama_update_argv():  return ["brew", "upgrade", "ollama"]
def ollama_install_argv(): return ["brew", "install", "ollama"]


_SEMVER_RE = re.compile(r"\d+(?:\.\d+)+")


def parse_semver(text: str) -> Optional[str]:
    """Pull the first dotted-numeric version out of mixed CLI banner text.

    Robust across the formats the seats actually print: "2.1.177 (Claude Code)",
    "codex-cli 0.135.0", a bare "0.38.2", or "0.46.0" from a manager.
    """
    if not text:
        return None
    m = _SEMVER_RE.search(text)
    return m.group(0) if m else None


def parse_npm_latest(stdout: str) -> Optional[str]:
    # `npm view <pkg> version` prints the bare version on its own line.
    return parse_semver(stdout)


def parse_brew_latest(stdout: str) -> Optional[str]:
    # `brew info --json=v2 <formula>` -> formulae[0].versions.stable. stdlib json,
    # no jq. Any shape surprise degrades to "unknown" rather than crashing preflight.
    try:
        data = json.loads(stdout)
        return data["formulae"][0]["versions"]["stable"]
    except (ValueError, KeyError, IndexError, TypeError):
        return None


def parse_brew_cask_latest(stdout: str) -> Optional[str]:
    # `brew info --json=v2 --cask <cask>` -> casks[0].version (e.g. "1.0.12,6156..."),
    # so reduce to the dotted-numeric head. antigravity-cli ships as a cask.
    try:
        data = json.loads(stdout)
        return parse_semver(data["casks"][0]["version"])
    except (ValueError, KeyError, IndexError, TypeError):
        return None


def version_tuple(version: Optional[str]) -> tuple:
    if not version:
        return ()
    try:
        return tuple(int(p) for p in version.split("."))
    except ValueError:
        return ()


def version_is_current(installed: Optional[str], latest: Optional[str]) -> Optional[bool]:
    """True if installed >= latest, False if behind, None if either is unknown.

    None ("can't judge") is deliberate: a missing package manager or an offline
    box must NOT read as "stale" and trigger a spurious update prompt.
    """
    iv, lv = version_tuple(installed), version_tuple(latest)
    if not iv or not lv:
        return None
    width = max(len(iv), len(lv))
    iv += (0,) * (width - len(iv))
    lv += (0,) * (width - len(lv))
    return iv >= lv


# Model-not-found signatures, grounded against live CLI output on 2026-06-25:
#   claude (stdout): "...may not exist or you may not have access to it."
#   codex  (stderr): {"type":"invalid_request_error","message":"The '...' model is not supported..."}
#   gemini (stderr): "ModelNotFoundError: Requested entity was not found."
# A pinned id that trips one of these on a smoke ping means the id is stale for
# the installed CLI — the trigger to update the CLI and/or propose a fallback id.
_MODEL_NOT_FOUND_SIGNALS = (
    "modelnotfound",
    "requested entity was not found",
    "may not exist or you may not have access",
    "issue with the selected model",
    "model is not supported",
    "is not supported when using codex",
    "model not found",
    "no such model",
    "unknown model",
)


def model_not_found(result: "SpawnResult") -> bool:
    blob = (result.stdout + "\n" + result.stderr).lower()
    return any(sig in blob for sig in _MODEL_NOT_FOUND_SIGNALS)


REGISTRY: dict = {
    "claude": SeatAdapter(
        name="claude",
        default_model="claude-opus-4-8",
        provider="Anthropic",
        default_reasoning="xhigh",
        build_argv=claude_argv,
        version_argv=claude_version,
        prompt_on_stdin=True,
        close_stdin=False,
        stderr_is_fatal=True,
        supports_isolation=True,
        isolates_network=True,   # --disallowed-tools WebSearch WebFetch removes web reach
        model_answered=parse_model_answered,
        latest_argv=claude_latest_argv,
        parse_latest=parse_npm_latest,
        update_argv=claude_update_argv,
        install_argv=claude_install_argv,
        auth_hint="run `claude` once and sign in (Claude subscription, or set ANTHROPIC_API_KEY)",
        pkg_label="npm @anthropic-ai/claude-code",
        flags_verified_version="2.1.177",
        fallback_models=(),   # Anthropic ids are stable; pin the current one, no guesses
    ),
    "codex": SeatAdapter(
        name="codex",
        default_model="gpt-5.5",
        provider="OpenAI",
        default_reasoning="xhigh",
        build_argv=codex_argv,
        version_argv=codex_version,
        prompt_on_stdin=False,
        close_stdin=True,   # the </dev/null fix — codex exec reads stdin to EOF
        stderr_is_fatal=True,
        supports_isolation=True,
        isolates_network=True,   # --sandbox read-only has no network (verified: DNS fails inside)
        model_answered=parse_model_answered,
        latest_argv=codex_latest_argv,
        parse_latest=parse_npm_latest,
        update_argv=codex_update_argv,
        install_argv=codex_install_argv,
        auth_hint="run `codex` once and sign in with your ChatGPT account (subscription preferred)",
        pkg_label="npm @openai/codex",
        flags_verified_version="0.135.0",
        fallback_models=(),
    ),
    "gemini": SeatAdapter(
        name="gemini",
        # GA id confirmed against Google's docs (2026-06-24): Gemini 3 Flash Preview
        # was renamed gemini-3-flash-preview -> gemini-3.5-flash on GA. The GA id
        # needs gemini-cli >= 0.46 to resolve; older CLIs 404 it, which is exactly
        # what the toolchain preflight detects and fixes (update CLI, or fall back).
        default_model="gemini-3.5-flash",
        provider="Google",
        default_reasoning="HIGH",
        build_argv=gemini_argv,
        version_argv=gemini_version,
        prompt_on_stdin=False,
        close_stdin=True,
        stderr_is_fatal=False,   # router retries on stderr are normal; judge by the artifact
        supports_isolation=True,    # fs scoping via cwd; network is NOT removable (below)
        isolates_network=False,  # no known flag disables GoogleSearch grounding — surfaced loudly
        model_answered=parse_model_answered,
        latest_argv=gemini_latest_argv,
        parse_latest=parse_brew_latest,
        update_argv=gemini_update_argv,
        install_argv=gemini_install_argv,
        auth_hint="run `gemini` once and authenticate (Google account; consumer tiers sunset 2026-06-18 — enterprise/API only)",
        pkg_label="brew gemini-cli",
        flags_verified_version="0.46.0",   # -m/-p/--approval-mode plan/--skip-trust verified on 0.46.0 (2026-06-25)
        # Ordered fallbacks to PROBE + PROPOSE (not auto-apply) if gemini-3.5-flash
        # 404s on a not-yet-updated CLI: the immediate predecessor first, then Pro.
        fallback_models=("gemini-3-flash-preview", "gemini-3.1-pro", "gemini-3-pro-preview"),
    ),
    "antigravity": SeatAdapter(
        name="antigravity",
        # Exact display name from `agy models` — agy silently substitutes an unknown
        # name, so this must match a listed model verbatim (verified on agy 1.0.12).
        default_model="Gemini 3.5 Flash (High)",
        provider="Google",
        default_reasoning="High",   # effort is part of the model name, not a flag
        build_argv=antigravity_argv,
        version_argv=antigravity_version,
        prompt_on_stdin=False,
        close_stdin=True,        # agy reads stdin to EOF — verified to hang without DEVNULL
        stderr_is_fatal=False,
        supports_isolation=True,    # cwd scoping + --sandbox terminal restrictions
        isolates_network=False,  # agent-first harness; web/grounding not removable — surfaced loudly
        model_answered=_model_answered_none,
        latest_argv=antigravity_latest_argv,
        parse_latest=parse_brew_cask_latest,
        update_argv=antigravity_update_argv,
        install_argv=antigravity_install_argv,
        auth_hint="run `agy` once and sign in (Google account; the gemini-cli successor)",
        pkg_label="brew --cask antigravity-cli",
        flags_verified_version="1.0.12",
        fallback_models=(),      # agy never 404s a model (it silently substitutes) — no probe to do
    ),
    "ollama": SeatAdapter(
        name="ollama",
        # A local model is user-chosen — this is a sensible, broadly-pullable default
        # to override with `--model ollama=<your pulled model>` (see `ollama list`).
        # Pinned inline per the model-id policy; no fallback probing, because what
        # resolves depends entirely on what the user has pulled locally, not on a
        # renamable hosted id (fallback_models=()).
        default_model="llama3.3",
        provider="local",          # NOT external egress — the privacy lever (data-handling.md)
        default_reasoning="default",   # local models have no reasoning-effort knob
        build_argv=ollama_argv,
        version_argv=ollama_version,
        prompt_on_stdin=True,      # `ollama run <model>` reads the prompt on stdin (like claude)
        close_stdin=False,
        stderr_is_fatal=False,     # ollama prints model-load / pull progress to stderr — not fatal
        supports_isolation=True,   # fs scoping via cwd; a local model has nothing external to scope
        isolates_network=True,     # local model: no external network at all (intrinsic, not a flag)
        model_answered=_model_answered_none,
        latest_argv=ollama_latest_argv,
        parse_latest=parse_brew_latest,
        update_argv=ollama_update_argv,
        install_argv=ollama_install_argv,
        auth_hint="no account needed — local models stay on your machine; pull one with "
                  "`ollama pull <model>` (see `ollama list`)",
        pkg_label="brew ollama",
        flags_verified_version="",  # ollama absent on the dev box — no live grounding to claim
        fallback_models=(),
    ),
}
