# 0005: Codex publication review boundaries

- Date: 2026-09-04
- Links: https://github.com/timharris707/skills/pull/286

The Codex edition must include every promoted skill. A catalog entry without its
generated Codex file therefore fails the site build; returning a successful build
with an edition-specific 404 would publish an incomplete catalog. Keep that
failure explicit. The package-generation and Markdown checks enforce the same
requirement independently.

The duplicated scope-filter implementations in Advisory Board remain unchanged
in this publication. Independent tests found identical secret, symlink-escape,
include, and exclude behavior. Deduplication is optional shared-source refactoring,
not a demonstrated security correction, and this edition preserves the original
Claude sources.

Historical Ingest attribution was already in public main. The Codex edition
nevertheless generalizes project provenance for a portable public package.
Sanitized replacements carry upstream hashes without repeating the old attribution
in adaptation patch deletions. Public authorship and license attribution remain.

GitHub's issue schema permits a dependency summary, but does not require it.
Unknown dependency state must not mean zero blockers. The Codex tracker recipe
uses the explicitly requested GraphQL summary and treats absent data as unknown.
