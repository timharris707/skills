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

Advisory Board's echo score retains its tested threshold: at least half the
considered seats must change toward the final majority. The original regression
explicitly expects one of two seats to count. Correct the misleading docstring;
changing this threshold would recalibrate the metric. Missing verdict tokens
provide no evidence of movement and are excluded from the flip counts.

The new release checkout at the validated tag applies only to `clickai-codex`.
Legacy release callers retain their original checkout behavior. The plugin has
no authentication-bearing components; its marketplace authentication policy
therefore causes no credential prompt or write during native installation.
