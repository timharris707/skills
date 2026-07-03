**1. Verdict**

Block, high confidence. What would change it: a patch that fixes the egress disclosure/consent wording, uses each endorsement seat’s own timeout, and removes the duplicate-provider revision-seat ambiguity, with regression tests for all three.

**2. Strongest Objections**

1. Egress disclosure is materially inaccurate. The endorsement prompt sends `original_source`, `revised_draft`, `edits_table`, and `unresolved_table` to non-revision seats, but the code and artifacts claim those seats see only material “already egressed.” The revised draft did not exist during the original rounds and was not already sent to every provider. This is a release-gate data-handling defect.

2. Endorsement spawns ignore per-seat timeout settings. `_run_endorsement_pass` passes `revision_seat.timeout_s` into every endorsement worker, and `run_endorsement()` then prefers that call-level timeout over the voting seat’s own resolved timeout. A user’s `--timeout codex=...` or `--timeout gemini=...` can be ignored.

3. Duplicate-provider provenance is still ambiguous for the revision seat. Endorsement rows/artifacts use unique ids, but `changes.revision_seat` is still written as `seat.name`, so a `claude,claude,codex` run cannot tell which Claude produced the draft from `changes.json`.

**3. Recommended Execution Sequence**

1. Fix egress language first: run card, runtime endorsement print, raw recorder text, docs. Say endorsement seats receive the original source, revised draft, and changes tables as derivative material under the existing run sensitivity/disclosure, not “already egressed” bytes.
2. Fix timeout resolution to mirror rounds: explicit call timeout, else `seat.timeout_s`, else adapter default. Do not pass the revision seat timeout to all endorsers.
3. Store and display the revision seat’s unique id where duplicate-provider identity matters, at least in `changes.revision_seat` and revision artifacts/logs if schema compatibility allows.
4. Add regressions: per-endorser timeout override, duplicate-provider `revision_seat`, and a consent/run-card assertion that names revised draft egress.
5. Re-run the full suite and one real mocked `--board claude,claude,codex --output revised-draft` flow.

**4. Invariants And Guardrails**

Keep the good parts: merge endorsement rows before writing `changes.json`, hash exactly the bytes written, and write the verdict pointer after that. Preserve deterministic row order: board order, then edit targets, then unresolved targets. Keep model output as tokens only; the conductor builds rows. Keep malformed endorsement replies all-or-dropped per seat, never partial.

**5. Risks / Missing Evidence**

I did not run the suite because this session is read-only and the test harness writes temp artifacts. The added tests also do not cover per-seat timeout behavior or the actual consent/egress wording. The duplicate-provider test comment contradicts its assertion, which is a sign the chosen revision-seat identity is not well understood.

**6. Concrete Evidence**

- [endorsement.py:252](skills/advisory-board/scripts/_conductor/endorsement.py:252) sends `original_source`; [endorsement.py:253](skills/advisory-board/scripts/_conductor/endorsement.py:253) sends `revised_draft`; [endorsement.py:254](skills/advisory-board/scripts/_conductor/endorsement.py:254) sends edit tables.
- [endorsement.py:247](skills/advisory-board/scripts/_conductor/endorsement.py:247) claims nothing egresses that the provider has not already seen.
- [cli.py:760](skills/advisory-board/scripts/_conductor/cli.py:760) prints the endorsement fan-out, and [cli.py:762](skills/advisory-board/scripts/_conductor/cli.py:762) says each seat sees material “the run already egressed.”
- [artifacts.py:143](skills/advisory-board/scripts/_conductor/artifacts.py:143) says endorsement is ON, but [artifacts.py:145](skills/advisory-board/scripts/_conductor/artifacts.py:145) says “no new egress.”
- [cli.py:766](skills/advisory-board/scripts/_conductor/cli.py:766) calls `run_endorsement_pass(... timeout=revision_seat.timeout_s ...)`; [endorsement.py:497](skills/advisory-board/scripts/_conductor/endorsement.py:497) then chooses the call timeout over adapter default, with no `seat.timeout_s` fallback.
- [revision.py:1001](skills/advisory-board/scripts/_conductor/revision.py:1001) records `revision_seat=seat.name`; [changes-schema.md:102](skills/advisory-board/references/changes-schema.md:102) describes it as “the board seat.”

**7. Ask Other Seats To Challenge**

Ask them whether the egress claim is acceptable under the existing data-handling contract, whether `changes.revision_seat` should become a unique id in `changes@1`, and whether failed endorsement internals should ever silently degrade to empty endorsements.

VERDICT: block
