# Measured evidence: the incidents behind orchestrate's cost rules

Reference, not protocol: the rules live in [SKILL.md](../SKILL.md); this file holds the measurements and incident history that earned them. Consult it when a rule's price tag is questioned: when a repo debates relaxing the cadence or the announce discipline.

## Idle-gap cache economics (SKILL.md §1 item 5)

A session's prompt cache expires after roughly five minutes of silence. A wake past the expiry re-writes the entire accumulated context at write price instead of reading it back at roughly a tenth of that; on an orchestrator-sized context, the per-wake difference is an order of magnitude.

Measured on a real orchestration run (2026-08): the cold re-caching from 7–13-minute idle gaps was the largest single avoidable cost of the session, ahead of everything the lanes themselves spent. The sub-TTL poll is "monitoring means polling" with the price tag attached: the poll that keeps the watch honest is the same poll that keeps the cache warm, and it is free relative to the cold wake it prevents. The cost exists only where the next wake carries a large context, which is why the cadence rule binds only while lanes are live.

The same burn comparison, re-run after the metronome landed, found the biggest remaining ramp was orchestrator context accumulation mid/late run: every wake re-reads the whole accumulated context at cache-read price, so whatever a wake ingests is paid again on every later wake. That finding produced the lean-wake rule and the scoped close-out audit (§1 item 5, §5 step 1).

A cold re-cache also leaves no visible trace: the transcript looks identical to a warm read, only the bill differs. That is why §5's close-out reports the longest between-wake gap and names any gap past the TTL as a cadence miss: the gap line is the only tripwire the miss has.

## Mid-flight model switches (SKILL.md §4)

The prompt cache is per-model. A measured run's two mid-session model flips each cost a full-context re-write at write price, on top of whatever behavioral reasons the switch had; a fresh subagent launched at the target model would have cost its own small first-write instead. Hence: a session's model is fixed at launch.

## The permission-wall mechanism (SKILL.md §4)

Why expected mid-flight approvals are the strongest subagent-vs-session discriminator: a subagent hitting a permission wall fails where a separate session can prompt the human and continue. Violating the discriminator doesn't inconvenience the lane: it kills it mid-flight, wasting the whole brief-out.

## Announce-compliance decay (SKILL.md §4/§5)

Measured over long real sessions: orchestrators followed the announce rule at launch and dropped the per-round repeats hours in: behavior decays where machinery doesn't. That finding split the discipline in two: prevention moves into a tool-call hook where the harness supports one ([announce-hook.md](announce-hook.md)), and detection is the close-out's `rounds announced: N of N` line. Neither substitutes for the other.
