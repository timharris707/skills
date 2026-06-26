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
from typing import Optional

__all__ = [
    "SECRET_DENYLIST",
    "resolve_scope",
    "scan_secrets",
    "build_scope_manifest",
    "scope_hash",
    "snapshot_scope",
    "cleanup_snapshot",
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
    if dest is None:
        dest = tempfile.mkdtemp(prefix="advisory-board-repo-")
    root_real = os.path.realpath(root)
    root_prefix = root_real if root_real.endswith(os.sep) else root_real + os.sep
    for rel in relpaths:
        rel = rel.replace("\\", "/")
        # Never write outside the snapshot dir: reject an absolute or '..'-bearing
        # rel so this can't become a write-traversal primitive for a bad/future caller.
        if os.path.isabs(rel) or any(part == ".." for part in rel.split("/")):
            continue
        src = os.path.join(root, rel)
        # Re-assert the resolve-time gate AT COPY TIME (TOCTOU defense): a file that
        # was a clean in-scope regular file when resolve_scope ran can be swapped for
        # a symlink-out before we copy. Drop symlinks outright (don't dereference) and
        # re-confine the realpath under the repo root, so copyfile can never pull an
        # out-of-root file's bytes (e.g. a private key) into the snapshot seats read.
        if os.path.islink(src):
            continue
        src_real = os.path.realpath(src)
        if not (src_real == root_real or src_real.startswith(root_prefix)):
            continue
        if not os.path.isfile(src_real):
            continue
        target = os.path.join(dest, rel)
        os.makedirs(os.path.dirname(target) or dest, exist_ok=True)
        shutil.copyfile(src, target)   # src is now a confirmed non-symlink regular file under root
        try:
            os.chmod(target, 0o444)
        except OSError:
            pass
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
