**1. Updated Verdict**

Block, high confidence. I would move to caution after the rubric proposal prompts are included in the approved/hash-bound egress surface, the disclosure names the rubric egress purpose, and chair mechanical invalid replies retry once before final refusal.

**2. Changed / Dissent**

Changed toward Claude: Claude’s disclosure objection is valid as a separate defect. `disclosure_line()` still says only `This review sends your source material...` and has grounding/revision/ask branches, but no rubric branch at `scripts/_conductor/egress.py:248-278`.

Still dissent with Claude’s caution: this is not just hygiene. Codex’s round-1 hash-binding objection survives the partial local fix: `_run_rubric_step()` rechecks `packet_hash(blobs)` at `scripts/_conductor/cli.py:682`, but those `blobs` are only round-1 prompts from `build_packet()`.

**3. Strongest Remaining Objections**

Blocker: rubric proposal prompt bytes are not in the approved packet. `build_packet()` only creates `prompts/<seat>-round-1.prompt` at `scripts/_conductor/egress.py:95-111`; `content_hash` is computed from that at `scripts/_conductor/cli.py:287-288`. The rubric prompt is generated later at `scripts/_conductor/rubric.py:885-912` and written only after spawn at `scripts/_conductor/cli.py:713-718`. Failure scenario: a non-public run approves hash H, but the first source-bearing egress is a different rubric prompt not present in the manifest or consent hash.

Blocker: chair partition/weight failures do not retry. The loop breaks after a syntactically parsed chair reply, then mechanical checks happen outside the retry loop at `scripts/_conductor/rubric.py:1022-1039`. That contradicts the contract’s “Any discrepancy makes the reply invalid (retryable once, then refusal path).” Failure scenario: chair first emits weights summing to 99; code refuses immediately instead of retrying once.

Concern: validator does not cross-check dropped provenance. `dropped[].seat/title` are only type-checked at `scripts/board_rubric.py:136-151`; partition validation only checks `proposal_id` membership at `scripts/board_rubric.py:247-257`. A hand-edited rubric can claim dropped `p4` came from the wrong seat/title and still validate.

Concern: default chair selection still uses a by-name dict at `scripts/_conductor/rubric.py:325-336`, collapsing duplicate providers for the default `claude` path. With `claude,claude,codex` and no `--chair-seat`, this silently picks one duplicate rather than applying a visibly unique-axis default.

**4. Recommended Execution Sequence**

1. Fix egress: prebuild rubric proposal `PacketBlob`s before approval, include them in the manifest/hash, update `disclosure_line()`, and spawn from those exact blobs.
2. Keep chair as derivative egress, but disclose that proposals go to the chair and record/reassert its packet hash.
3. Move chair mechanical rejection into the two-attempt retry loop for model-authored partition/weight/schema failures.
4. Tighten validator provenance cross-checks and duplicate-provider default chair behavior.
5. Add tests that fail if `--rubric` prompt files are absent from the approved manifest/hash, and tests proving bad chair weight/partition makes two attempts before refusal.

**5. Invariants And Guardrails**

Every source-bearing external prompt must be approved by exact bytes or be a disclosed derivative with its own recorded packet hash. No opinion round runs after rubric refusal. Proposal ids, criterion ids, partition coverage, and weight arithmetic remain conductor-owned. No-`--rubric` runs must stay byte-identical.

**6. Risks / Missing Evidence**

The stale assumption is “same source plus same providers means same consent.” This system’s own egress model says consent binds to exact packet bytes. The current tests mostly assert artifacts and refusal outcomes; they do not prove the rubric prompts are in the approved manifest, and they currently pin the wrong chair no-retry behavior at `tests/test_run_board.py:15287-15309`.

**7. Concrete Evidence**

`build_packet()` round-1 only: `scripts/_conductor/egress.py:95-111`.  
Rubric prompt generated/spawned later: `scripts/_conductor/rubric.py:885-912`.  
Rubric prompt persisted after spawn: `scripts/_conductor/cli.py:713-718`.  
Disclosure lacks rubric branch: `scripts/_conductor/egress.py:248-278`.  
Mechanical checks outside retry loop: `scripts/_conductor/rubric.py:1022-1039`.

BASIS: independent
VERDICT: block
