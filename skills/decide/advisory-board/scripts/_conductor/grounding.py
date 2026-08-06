"""Repo-grounding scope resolution, read-only snapshot, and the scope manifest
(design/run-board-repo-grounding.md — P1).

Repo-grounded review lets board seats read the actual codebase. That widens the
egress surface (a seat can quote any file it reads) and the injection surface, so
the *first* thing this module does is BOUND what a seat may read to a stable,
secret-free, symlink-confined set — and produce a hashable manifest the egress
consent binds to (P2) and the snapshot the seats are pointed at (P3).

The scope is, in order:
  1. the repo's own view of its files — `git ls-files --cached --others
     --exclude-standard` when the path is a git repo (this is what respects
     `.gitignore` for free); a plain os.walk fallback otherwise;
  2. minus a hard SECRET/VCS denylist (`.git`, `.env*`, keys, creds) applied to
     every path segment — belt-and-suspenders even if `.gitignore` missed them;
  3. minus anything that escapes the repo root via a symlink (realpath-confined);
  4. narrowed by optional include/exclude globs.

A content secret-scan (`scan_secrets`) runs over the resolved set and is surfaced
to the user BEFORE approval — advisory, never silently dropping a key a
`.gitignore` missed. Nothing here egresses; this is all local, read-only.
"""
from __future__ import annotations

import fnmatch
import hashlib
import os
import re
import shutil
import stat
import subprocess
from dataclasses import dataclass
from typing import Optional

__all__ = [
    "SECRET_DENYLIST",
    "resolve_scope",
    "resolve_scope_with_method",
    "scan_secrets",
    "build_scope_manifest",
    "scope_hash",
    "snapshot_scope",
    "cleanup_snapshot",
    "GroundingContext",
    "prepare_grounding",
    "rehash_snapshot",
    "render_repo_scope_lines",
    "strip_repo_quote_bodies",
    "quoted_repo_paths",
]

# Path segments (basename or any dir component) that are NEVER in scope, even if
# `.gitignore` would include them. Matched case-insensitively as fnmatch globs
# against each '/'-split segment of the relative path. The control here is a
# denylist, not a sandbox: it stops the obvious secret/VCS classes from being
# snapshotted and egressed; it is not a guarantee no secret exists in scope (that
# is what scan_secrets surfaces).
SECRET_DENYLIST = (
    ".git",
    ".env", ".env.*", "*.env", ".envrc",
    "*.pem", "*.key", "*.p12", "*.pfx", "*.keystore", "*.jks", "secring.*",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",   # specific key basenames (not a bare id_* — that ate source files)
    ".npmrc", ".pypirc", ".netrc", ".htpasswd",
    "credentials", "credentials.*", "*-credentials", "*-credentials.*",
    "client_secret*.json", "*service-account*.json", "*-sa.json",
    "secrets", "*.secret", "secrets.*", "*-secrets.*",   # exact/anchored, not a *secret* substring that ate secrets_manager.py
    "*.tfstate", "*.tfstate.*", "*.tfvars",
    "kubeconfig", "*.kubeconfig", "*.token",
    ".aws", ".ssh", ".gnupg", ".docker",
)

# Heuristic content signatures for an accidental secret left in an in-scope file.
# Advisory only — a hit is surfaced before approval, never auto-fatal (the user
# may know it is a fixture). Mirrors the data-handling "never send secrets" rule.
_SECRET_CONTENT = re.compile(
    r"(AKIA[0-9A-Z]{16}"                                  # AWS access key id
    r"|aws_secret_access_key\s*[=:]"                      # AWS secret access key (assignment)
    r"|-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP |ENCRYPTED )?PRIVATE KEY-----"  # private key block (incl. ENCRYPTED)
    r"|xox[baprs]-[0-9A-Za-z-]{10,}"                      # slack token
    r"|gh[pousr]_[0-9A-Za-z]{36,}"                        # github token (classic)
    r"|github_pat_[0-9A-Za-z_]{50,}"                      # github fine-grained PAT
    r"|AIza[0-9A-Za-z_\-]{35}"                            # google api key
    r"|sk-(?:proj-|ant-)?[0-9A-Za-z_\-]{20,}"            # openai / anthropic-style secret key
    r"|sk_live_[0-9A-Za-z]{16,}"                          # stripe live secret key
    r"|eyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+)"  # JWT
)
_SCAN_MAX_BYTES = 1_000_000   # don't scan-read a file larger than this (likely a binary/asset)


def _git_candidates(root: str) -> Optional[list]:
    """Repo-relative files git knows about, minus gitignored-untracked. None if git
    is absent / not a repo / errors (→ the os.walk fallback). Read in BYTES mode and
    decoded with surrogateescape so a non-UTF8 path in the index round-trips intact
    instead of crashing the resolver with an uncaught UnicodeDecodeError."""
    try:
        out = subprocess.run(
            ["git", "-C", root, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return [p.decode("utf-8", "surrogateescape") for p in out.stdout.split(b"\0") if p]


def _walk_candidates(root: str) -> list:
    """os.walk fallback for a non-git dir: every file, denylisted dirs pruned."""
    rels = []
    for dirpath, dirnames, filenames in os.walk(root):
        # prune denied directories in place so we don't descend into .git/secrets/etc.
        dirnames[:] = [d for d in dirnames if not _denied(d)]
        for name in filenames:
            full = os.path.join(dirpath, name)
            rels.append(os.path.relpath(full, root))
    return rels


def _denied(segment_or_path: str) -> bool:
    """True if ANY '/'-split segment matches a denylist glob (case-insensitive)."""
    segments = segment_or_path.replace("\\", "/").split("/")
    for seg in segments:
        low = seg.lower()
        for pat in SECRET_DENYLIST:
            if fnmatch.fnmatch(low, pat.lower()):
                return True
    return False


def _within_root(root_real: str, relpath: str) -> bool:
    """Realpath-confine: the file must resolve to a path INSIDE the repo root,
    so a symlink (or '..') cannot pull a file from outside the declared scope."""
    full = os.path.realpath(os.path.join(root_real, relpath))
    root_prefix = root_real if root_real.endswith(os.sep) else root_real + os.sep
    return full == root_real or full.startswith(root_prefix)


def _matches_any(relpath: str, globs) -> bool:
    rp = relpath.replace("\\", "/")
    base = os.path.basename(rp)
    for g in globs:
        if fnmatch.fnmatch(rp, g) or fnmatch.fnmatch(base, g):
            return True
    return False


def resolve_scope_with_method(root: str, include=None, exclude=None) -> tuple:
    """Like resolve_scope but also reports HOW the candidate set was produced:
    ('git', scope) when `git ls-files` drove it (so .gitignore was applied), or
    ('walk', scope) when the os.walk fallback drove it (a non-git tree — .gitignore
    is NOT applied there). The consent disclosure (render_repo_scope_lines) uses this
    so it can't claim '.gitignore'd paths excluded' for a tree where git never ran."""
    if not os.path.isdir(root):
        raise ValueError(f"--repo is not a directory: {root}")
    root_real = os.path.realpath(root)
    candidates = _git_candidates(root)
    if candidates is None:
        method = "walk"
        candidates = _walk_candidates(root)
    else:
        method = "git"

    include = list(include or [])
    exclude = list(exclude or [])
    scope = []
    seen = set()
    for rel in candidates:
        rel = rel.replace("\\", "/").lstrip("/")
        if not rel or rel in seen:
            continue
        if _denied(rel):
            continue
        if not _within_root(root_real, rel):
            continue
        full = os.path.join(root_real, rel)
        # must be (or resolve to) a real regular file under the root
        if not os.path.isfile(full):
            continue
        if include and not _matches_any(rel, include):
            continue
        if exclude and _matches_any(rel, exclude):
            continue
        seen.add(rel)
        scope.append(rel)
    return method, sorted(scope)


def resolve_scope(root: str, include=None, exclude=None) -> list:
    """Return the sorted repo-relative file list a grounded seat may read.

    git-aware (respects .gitignore) with an os.walk fallback; minus the SECRET
    denylist (any path segment), minus symlink/`..` escapes (realpath-confined to
    root), narrowed by optional include/exclude fnmatch globs. Regular files only
    (symlinks-to-files that resolve inside root are kept; symlinks out are dropped)."""
    if not os.path.isdir(root):
        raise ValueError(f"--repo is not a directory: {root}")
    root_real = os.path.realpath(root)
    candidates = _git_candidates(root)
    if candidates is None:
        candidates = _walk_candidates(root)

    include = list(include or [])
    exclude = list(exclude or [])
    scope = []
    seen = set()
    for rel in candidates:
        rel = rel.replace("\\", "/").lstrip("/")
        if not rel or rel in seen:
            continue
        if _denied(rel):
            continue
        if not _within_root(root_real, rel):
            continue
        full = os.path.join(root_real, rel)
        # must be (or resolve to) a real regular file under the root
        if not os.path.isfile(full):
            continue
        if include and not _matches_any(rel, include):
            continue
        if exclude and _matches_any(rel, exclude):
            continue
        seen.add(rel)
        scope.append(rel)
    return sorted(scope)


def scan_secrets(root: str, relpaths) -> list:
    """Advisory content scan over the in-scope files. Returns [(relpath, signature)]
    for any file whose text matches a known secret signature — surfaced before
    approval, never auto-fatal (the file may be a deliberate fixture)."""
    hits = []
    for rel in relpaths:
        full = os.path.join(root, rel)
        try:
            size = os.path.getsize(full)
            with open(full, "rb") as handle:
                raw = handle.read(_SCAN_MAX_BYTES)   # bounded PREFIX — never skip silently
        except OSError:
            continue
        text = raw.decode("utf-8", "ignore")
        m = _SECRET_CONTENT.search(text)
        if m:
            label = m.group(0)
            kind = label[:12] + "…" if len(label) > 12 else label  # never echo the full secret
            hits.append((rel, kind))
        elif size > _SCAN_MAX_BYTES:
            # an oversized in-scope file with no hit in its prefix is NOT certified
            # clean — emit an explicit marker so the consent surface can say so.
            hits.append((rel, f"<unscanned tail: {size} B > {_SCAN_MAX_BYTES} scanned>"))
    return hits


def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_scope_manifest(root: str, relpaths) -> dict:
    """A hashable description of the read surface: per-file path/size/sha256 plus
    totals and a single scope_hash. The egress consent (P2) binds to scope_hash so
    'what a seat could read' is part of what the user approved."""
    files = []
    total = 0
    for rel in sorted(relpaths):
        full = os.path.join(root, rel)
        try:
            size = os.path.getsize(full)
            digest = _file_sha256(full)
        except OSError:
            continue
        files.append({"path": rel, "size": size, "sha256": digest})
        total += size
    return {
        "root": os.path.abspath(root),
        "n_files": len(files),
        "n_bytes": total,
        "files": files,
        "scope_hash": scope_hash(files),
    }


def scope_hash(files) -> str:
    """sha256 over the sorted (path, size, sha256) triples — order-independent,
    content-bound. Mirrors egress.packet_hash's discipline (consent binds to a hash)."""
    h = hashlib.sha256()
    for f in sorted(files, key=lambda x: x["path"]):
        h.update(f"{f['path']}\0{f['size']}\0{f['sha256']}\n".encode("utf-8"))
    return h.hexdigest()


def snapshot_scope(root: str, relpaths, dest: Optional[str] = None) -> str:
    """Copy the in-scope files into a fresh read-only directory and return its path.

    Seats are pointed at this SNAPSHOT (P3), not the live tree, so: the bytes are
    stable between approval and spawn (no drift), there are no out-of-root symlinks
    to follow, and `verify` later resolves citations against exactly what the seats
    saw. Files are chmod'd read-only (0o444) as defense-in-depth; the seat adapters'
    read-only sandboxes are the primary write-block."""
    import tempfile
    created_here = dest is None
    if dest is None:
        dest = tempfile.mkdtemp(prefix="advisory-board-repo-")
    root_real = os.path.realpath(root)
    root_prefix = root_real if root_real.endswith(os.sep) else root_real + os.sep
    try:
        for rel in relpaths:
            rel = rel.replace("\\", "/")
            # Never write outside the snapshot dir: reject an absolute or '..'-bearing
            # rel so this can't become a write-traversal primitive for a bad/future caller.
            if os.path.isabs(rel) or any(part == ".." for part in rel.split("/")):
                continue
            src = os.path.join(root, rel)
            # Re-assert the resolve-time gate AT COPY TIME (TOCTOU defense): a file that
            # was a clean in-scope regular file when resolve_scope ran can be swapped for
            # a symlink-out before we copy. The realpath-confinement below is a cheap
            # PRE-FILTER only; the load-bearing defense is opening the source with
            # O_NOFOLLOW and copying from the HELD descriptor (never re-resolving the
            # path), so a symlink swapped in after this point cannot redirect the copy.
            if os.path.islink(src):
                continue
            src_real = os.path.realpath(src)
            if not (src_real == root_real or src_real.startswith(root_prefix)):
                continue
            # Close the TOCTOU window: open by path with O_NOFOLLOW (raises OSError/ELOOP
            # if `src` is a symlink at open time), confirm via fstat that the OPEN fd is a
            # regular file, then stream the bytes of THAT fd into the target. Because the
            # check (fstat) and the use (os.read) are the same already-open object, a
            # later swap of `src` to an out-of-root symlink can never be followed — the
            # descriptor still points at the original regular file.
            try:
                src_fd = os.open(src, os.O_RDONLY | os.O_NOFOLLOW)
            except OSError:
                continue   # a symlink swapped in (ELOOP) or vanished file — drop it
            try:
                st = os.fstat(src_fd)
                if not stat.S_ISREG(st.st_mode):
                    continue   # not a regular file (a fifo/dir/device snuck in) — drop it
                target = os.path.join(dest, rel)
                os.makedirs(os.path.dirname(target) or dest, exist_ok=True)
                # O_EXCL: the target must not pre-exist (a fresh mkdtemp dest), so we never
                # clobber/append; copy from the held fd, not the re-resolved source path.
                dst_fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                try:
                    while True:
                        chunk = os.read(src_fd, 65536)
                        if not chunk:
                            break
                        os.write(dst_fd, chunk)
                finally:
                    os.close(dst_fd)
            finally:
                os.close(src_fd)
            try:
                os.chmod(target, 0o444)
            except OSError:
                pass
    except BaseException:
        # A copy failure mid-loop (ENOSPC, a Ctrl-C) would otherwise leave a partial
        # snapshot behind. If WE created the dir, clean it up before re-raising so the
        # "never leave a snapshot behind" invariant holds even on the error path.
        if created_here:
            cleanup_snapshot(dest)
        raise
    return dest


def cleanup_snapshot(dest: str) -> None:
    """Remove a snapshot tree even though its files are chmod'd read-only: an
    onerror hook restores write permission and retries, so 0o444 files don't
    block teardown (the conductor must never leave a snapshot behind)."""
    def _chmod_retry(func, path, _exc):
        try:
            parent = os.path.dirname(path)
            if parent:
                os.chmod(parent, 0o700)   # a read-only PARENT dir blocks unlink of its children
            os.chmod(path, stat.S_IRWXU)
            func(path)
        except OSError:
            pass
    shutil.rmtree(dest, onerror=_chmod_retry)


# P2 — consent & disclosure (design/run-board-repo-grounding.md Phase 2)
#
# The egress consent already binds to a sha256 of the exact prompt bytes that
# leave (egress.packet_hash). Repo-grounding makes a seat's REPLY a second egress
# channel — a seat can quote any in-scope file, and round 2+ fans that reply out to
# the OTHER providers. So consent must also bind to the repo SCOPE: the manifest of
# files a seat could read. GroundingContext is that scope, resolved+snapshotted+
# hashed once at pre-spawn and carried on RunConfig; everything below renders or
# re-checks it without ever widening the read surface past what was disclosed.


@dataclass
class GroundingContext:
    """The resolved, snapshotted, hashed read-surface for one grounded run.

    Computed once at pre-spawn (cli.cmd_run) and stored on RunConfig.grounding so
    every consent surface (manifest, run-card, sensitivity.json, run-metadata) reads
    ONE source of truth and can never disagree about what a seat could read. The
    egress consent binds to `scope_hash` alongside the prompt-packet hash; the
    round-1 drift guard re-hashes `snapshot_dir`; `verify` later resolves citations
    against the snapshot. `secret_hits` is the advisory content-scan surfaced before
    approval (the kind is truncated — never the full secret). `content_lines` is the
    fingerprint set of in-scope file lines D8 uses to elide verbatim repo bodies from
    the cross-reading packet, fence-agnostically."""
    repo_root: str
    snapshot_dir: Optional[str]
    manifest: dict
    secret_hits: list
    include: Optional[list] = None
    exclude: Optional[list] = None
    content_lines: frozenset = frozenset()
    # How the ORIGINAL --repo tree's scope was resolved: 'git' (git ls-files drove
    # it, so .gitignore was applied to untracked files) or 'walk' (a non-git tree —
    # .gitignore is NOT applied). render_repo_scope_lines renders an HONEST exclusion
    # disclosure conditioned on this (a non-git tree must not claim gitignored paths
    # are excluded; the git path must not imply tracked-but-ignored files are excluded).
    resolution_path: str = "git"

    @property
    def scope_hash(self) -> str:
        return self.manifest["scope_hash"]

    @property
    def n_files(self) -> int:
        return self.manifest["n_files"]

    @property
    def n_bytes(self) -> int:
        return self.manifest["n_bytes"]

    @property
    def files(self) -> list:
        return self.manifest.get("files", [])

    @property
    def scope_paths(self) -> list:
        return [f["path"] for f in self.manifest.get("files", [])]


def prepare_grounding(config, *, snapshot: bool = True) -> GroundingContext:
    """Resolve the scope, (optionally) snapshot it read-only, then hash + secret-scan
    the exact bytes a seat could read.

    With snapshot=True (a real run) the manifest and scan are computed over the
    SNAPSHOT — the frozen copy seats read and `verify` resolves against — so consent
    binds to what actually leaves, not a live tree that can drift between approval and
    spawn (R7), and the manifest can never overstate scope (a TOCTOU-dropped file is
    simply not in the snapshot). snapshot=False (a --dry-run preview) hashes the live
    tree for display only and creates no temp dir. The disclosed root is always the
    user's --repo path, never the throwaway snapshot tempdir (R9)."""
    repo = config.repo
    include = list(config.repo_include) if config.repo_include else None
    exclude = list(config.repo_exclude) if config.repo_exclude else None
    # Resolve the ORIGINAL --repo tree and record whether git or the os.walk fallback
    # drove it — this is the user-facing fact the exclusion disclosure must be honest
    # about. (The snapshot is re-resolved below, but a snapshot has no .git, so its
    # method is always 'walk' and would be the wrong thing to disclose.)
    resolution_path, relpaths = resolve_scope_with_method(repo, include=include, exclude=exclude)
    if snapshot:
        snap = snapshot_scope(repo, relpaths)
        # Everything after the snapshot is created must clean it up on ANY failure
        # (ENOSPC while hashing, a Ctrl-C), or the temp dir leaks — config.grounding
        # is only assigned by the caller once this returns, so the caller's finally
        # cannot see the dir yet. cleanup_snapshot + re-raise closes that window.
        try:
            snap_rel = resolve_scope(snap)             # what actually LANDED (post-TOCTOU-drop)
            manifest = build_scope_manifest(snap, snap_rel)
            hits = scan_secrets(snap, snap_rel)
            content = _repo_content_lines(snap, snap_rel)
        except BaseException:
            cleanup_snapshot(snap)
            raise
        snapshot_dir = snap
    else:
        # Preview (--dry-run): hash the LIVE tree, but apply the snapshot's own
        # drop-all-symlinks policy first, so the previewed scope hash equals the hash
        # the real run will snapshot+consent to (snapshot_scope drops in-root symlinks
        # that resolve_scope keeps; without this the preview over-lists them and shows
        # a hash the real run never reproduces).
        preview_rel = [r for r in relpaths if not os.path.islink(os.path.join(repo, r))]
        manifest = build_scope_manifest(repo, preview_rel)
        hits = scan_secrets(repo, preview_rel)
        content = _repo_content_lines(repo, preview_rel)
        snapshot_dir = None
    # Disclose the user's repo path, not the host tempdir the snapshot lives in.
    manifest["root"] = os.path.abspath(repo)
    return GroundingContext(repo_root=os.path.abspath(repo), snapshot_dir=snapshot_dir,
                            manifest=manifest, secret_hits=hits,
                            include=include, exclude=exclude, content_lines=content,
                            resolution_path=resolution_path)


def rehash_snapshot(snapshot_dir: str) -> str:
    """Recompute the scope hash from the snapshot's CURRENT bytes. The round-1 drift
    guard compares this to the approved scope hash — a snapshot file added, removed,
    or mutated between approval and spawn changes the hash and refuses the run, the
    same pre-spawn hard stop the packet hash already enforces (R7)."""
    rel = resolve_scope(snapshot_dir)
    return build_scope_manifest(snapshot_dir, rel)["scope_hash"]


def render_repo_scope_lines(grounding: "GroundingContext") -> list:
    """The shared 'readable repository scope' facts block, reused by the egress
    manifest, the run-card, and run-metadata so every consent surface states the SAME
    thing: the root, the totals, the scope hash consent binds to, what was excluded,
    the symlink policy, and any advisory secret-scan hits."""
    inc = ", ".join(grounding.include) if grounding.include else "(all in-scope files)"
    exc = ", ".join(grounding.exclude) if grounding.exclude else "(none)"
    # HONEST exclusion disclosure (R: false ".gitignore'd excluded" claim). The git
    # path uses `git ls-files --cached`, so a file that is TRACKED but later gitignored
    # stays in scope — only UNTRACKED gitignored paths are excluded. The os.walk
    # fallback (a non-git tree) never reads .gitignore at all, so claiming gitignored
    # paths are excluded there would be a false promise; only the secret denylist
    # excludes files in that case.
    if grounding.resolution_path == "walk":
        excluded_line = (
            "Excluded always : .git/ and the secret denylist (.env*, keys, credentials, "
            "tokens); symlinks resolving outside the root are dropped. NOTE: .gitignore is "
            "NOT applied (non-git tree) — only the secret denylist excludes files.")
    else:
        excluded_line = (
            "Excluded always : .git/, untracked .gitignore'd paths, and the secret denylist "
            "(.env*, keys, credentials, tokens); symlinks resolving outside the root are "
            "dropped. NOTE: a TRACKED file later added to .gitignore stays in scope.")
    lines = [
        f"Repository root : {grounding.repo_root}",
        f"Readable files  : {grounding.n_files} file(s), {grounding.n_bytes} bytes "
        "(a seat may read & quote any of them)",
        f"Scope hash      : sha256:{grounding.scope_hash}",
        f"Include globs   : {inc}",
        f"Exclude globs   : {exc}",
        excluded_line,
    ]
    # Per-file visibility (R: the consent surface showed only totals, never the in-scope
    # paths — leaving the secret-scan as the only per-file signal). Point the user at the
    # persisted full list AND inline the first paths so an unexpected secret-bearing file
    # can be spotted by name even when the content scan misses it.
    paths = grounding.scope_paths
    if paths:
        lines.append(f"Full readable file list: repo-scope-manifest.json ({len(paths)} file(s))")
        preview = paths[:10]
        lines.append("In-scope files  : " + ", ".join(preview)
                     + (f", … (+{len(paths) - len(preview)} more)" if len(paths) > len(preview) else ""))
    if grounding.secret_hits:
        lines.append(
            f"⚠ Secret-scan   : {len(grounding.secret_hits)} in-scope file(s) matched a "
            "secret signature — REVIEW before approving (the snapshot still contains them):")
        for rel, kind in grounding.secret_hits[:20]:
            lines.append(f"    - {rel} ({kind})")
        extra = len(grounding.secret_hits) - 20
        if extra > 0:
            lines.append(f"    - … (+{extra} more)")
    else:
        lines.append("Secret-scan     : no in-scope file matched a known secret signature (advisory).")
    return lines


# D8 — strip verbatim repo bodies from the round-N cross-reading packet.
#
# A seat under `--cross-reading full` shares its whole review verbatim with the OTHER
# providers in round 2+. If that review pasted a large chunk of an in-scope file, the
# bytes broadcast to providers that only ever needed the seat's REASONING (R6). D8
# elides those bodies. The signal is CONTENT, not formatting: we fingerprint every
# non-trivial in-scope file line — stripping a leading line-number prefix AND a single
# per-line quote/diff decoration (`> ` blockquote, `| ` table, `- `/`+ ` diff) so an
# idiomatically-quoted body still matches — then elide any run of ≥ min_lines packet
# lines that are verbatim in-scope content, fence or no fence. This is deliberately
# fence-AGNOSTIC: an earlier fence-toggle version leaked on unfenced quotes and desynced
# on files that themselves contain ``` lines. A single interleaved prose line within a
# run is tolerated (a small gap budget) so it can't chop a verbatim body into
# sub-threshold runs. Best-effort (a reflowed/paraphrased quote is no longer "verbatim"
# and is out of D8's scope; a file of all-short lines under the fingerprint floor is
# too); the load-bearing exfil control is D4 (no un-isolatable seat on a gate+repo
# board), not this. `path:line` citations are single prose lines, never a ≥min_lines
# content run, so they survive.

# A SINGLE leading per-line quote/diff decoration: markdown blockquote `> `, table
# `| `, or a diff marker `- `/`+ `. Stripped ONCE, ahead of the line-number prefix, so
# a blockquoted/diffed verbatim quote still fingerprints to the same content as the
# undecorated repo line. The `-`/`+` arm requires a FOLLOWING space and a non-digit
# next char so we don't eat a real code token: a unary minus glued to its operand
# (`-x`), a `+=`, or a signed number (`-42`, `+ 5`) keeps its leading char.
_QUOTE_DECORATION = re.compile(r"^\s*(?:[>|]|[-+](?=\s)(?!\s*[-+]?\d))\s?")
_LINE_NUM_PREFIX = re.compile(r"^\s*\d+\s*[:|]\s?")   # strip "42: " / "  42| " quote prefixes
_MIN_FINGERPRINT_LEN = 12    # ignore trivial lines ('}', '', 'return') — they'd false-match
_REPO_QUOTE_MIN_LINES = 8    # a verbatim content run of this many lines or more is elided
_RUN_GAP_BUDGET = 1          # non-blank prose lines tolerated WITHIN a run before it breaks


def _fingerprint(line: str) -> Optional[str]:
    """A line's content fingerprint for D8 matching: the line minus a single leading
    quote/diff decoration (`> `, `| `, `- `, `+ `) AND a leading line-number quote
    prefix, then surrounding whitespace, or None if it is too trivial to be a
    meaningful match (blank, a lone brace, a keyword). The decoration strip is applied
    symmetrically on both sides (it builds repo_lines AND matches packet lines), so a
    blockquoted/diffed verbatim quote matches the undecorated in-scope line."""
    core = _QUOTE_DECORATION.sub("", line, count=1)
    core = _LINE_NUM_PREFIX.sub("", core).strip()
    return core if len(core) >= _MIN_FINGERPRINT_LEN else None


def _repo_content_lines(root: str, relpaths) -> frozenset:
    """The set of non-trivial line fingerprints across the in-scope files — D8 matches
    a packet's lines against this to detect a verbatim repo body regardless of how the
    seat formatted the quote. Read once at pre-spawn from the same bytes consent binds
    to (the snapshot)."""
    lines: set = set()
    for rel in relpaths:
        full = os.path.join(root, rel)
        try:
            with open(full, "r", encoding="utf-8", errors="ignore") as handle:
                for raw in handle:
                    fp = _fingerprint(raw)
                    if fp:
                        lines.add(fp)
        except OSError:
            continue
    return frozenset(lines)


def strip_repo_quote_bodies(text: str, repo_lines, *,
                            min_lines: int = _REPO_QUOTE_MIN_LINES) -> str:
    """D8: elide runs of ≥ min_lines consecutive packet lines that are VERBATIM in-scope
    repo content (matched by `repo_lines` fingerprints), so one grounded seat's file
    quote does not broadcast verbatim to the OTHER providers in round 2+ (R6). Blank
    lines inside a run are tolerated (a code block has them) and up to `_RUN_GAP_BUDGET`
    non-blank prose lines are tolerated as interleaved commentary, so a single prose
    line every few content lines can't chop a verbatim body into sub-threshold runs;
    neither counts toward the run. A run of `min_lines` matched lines or more is elided.
    Only the matched span itself is replaced — tolerated trailing prose/blank lines
    (e.g. a terse `REVISE.` verdict after the quote) are emitted verbatim, never
    swallowed into the placeholder. Returns `text` unchanged when `repo_lines` is empty.
    Pure and idempotent; only called on a grounded run, so ungrounded packets are
    byte-identical to before."""
    if not repo_lines:
        return text
    src = text.splitlines()
    n = len(src)
    out: list = []
    i = 0
    while i < n:
        # Measure the run starting at i: contiguous in-scope content lines (counts),
        # blank lines (neutral, unlimited — code blocks have them), and — once the run
        # has already matched a content line — up to _RUN_GAP_BUDGET non-blank prose
        # lines (neutral, tolerated as INTERLEAVED commentary so a lone interjection
        # can't chop a verbatim body into sub-threshold runs). A prose line before any
        # match, or one beyond the gap budget, breaks the run. Track the index just past
        # the LAST matched content line so a trailing tolerated prose line (a terse
        # verdict) is emitted verbatim, never absorbed into the elided span.
        j = i
        matched = 0
        gap = 0
        last_match_end = i
        while j < n:
            fp = _fingerprint(src[j])
            if fp is not None and fp in repo_lines:
                matched += 1
                j += 1
                last_match_end = j
            elif src[j].strip() == "":
                j += 1                 # blank: neutral, keeps the run alive
            elif matched and gap < _RUN_GAP_BUDGET:
                gap += 1               # interior prose interjection: tolerated, doesn't count
                j += 1
            else:
                break                  # leading prose, or prose past the budget, ends the run
        if matched >= min_lines:
            out.append(f"[repo quote elided — {matched} verbatim in-scope line(s); see the "
                       "seat's full round review in round-N/<seat>.md]")
            i = last_match_end         # resume AFTER the quote, not past trailing prose
        else:
            out.append(src[i])         # not a quote run — emit one line, rescan from the next
            i += 1
    return "\n".join(out) + ("\n" if text.endswith("\n") else "")


def quoted_repo_paths(reply: str, scope_paths) -> list:
    """Best-effort post-hoc accounting: which in-scope repo paths a seat's reply
    actually mentions. The pre-spawn scope hash bounds what a seat COULD read; this
    records what it appears to have cited. A plain substring match on the relpath, so
    it over- rather than under-counts — an honest 'what was referenced', not a proof
    of what was read."""
    if not reply:
        return []
    return sorted({rel for rel in scope_paths if rel and rel in reply})
