# Guided Intake: the wizard

Every board run has a user-authorized plan covering mode, seats, lenses, effort, rounds, output, and data handling. Reuse a complete plan already approved in the current request or a recorded decision. Ask only for material missing or changed choices. `use defaults` resolves choices only after the user can review the concrete seats and costs; it never waives the two-seat minimum or data-handling authorization.

Use the available Codex question tool and its current schema, as described by grilling. Present small coherent batches with the recommendation first. Use free-text questions for missing facts and honor pending required answers; elapsed time is not consent.

## Step 1: Authorized preflight

Inspect CLI capabilities first. Doctor performs smoke calls across registered providers, so announce the call count and rough usage and check provider authorization before running it. For a subset, use individual version/auth checks and one authorized smoke call per proposed provider unless the installed command supports selection. Use the unverified/GO/NO-GO definitions in [preflight.md](preflight.md). Unverified providers may be presented as candidates for approval, but only approved GO seats are launch-ready. Unapproved providers are not contacted, including Anthropic smoke calls; missing authorization is not a technical failure.

Report per-seat status in plain terms, e.g. `grok: installed but not logged in` or `gemini: CLI missing`, and for each broken seat offer exactly three choices:

- **Fix it now.** With the user's yes, run the install/update via `run_board.py toolchain --install/--update`. Authentication is always the user's hands: print the auth command, wait, then re-probe. Never install or update anything without a yes on the card.
- **Continue without it.** The board proceeds smaller; the missing seat is named in the run plan.
- **Abort.** Stop cleanly.

## Step 2: Goal, then mode

Reuse the user's stated goal and chosen mode. If either is missing, ask for the goal or recommend a mode with its alternatives from `references/modes.md` §Choosing a mode; the user resolves a materially open choice.

The stated goal also settles the lens preset recommendation (`references/lens-presets.md`) and, when it names a repo or code, whether to offer `--repo` grounding.

## Step 3: Seats

Offer the GO providers. **"Latest frontier of each"** is the one-tap shortcut; any subset of 2–10 seats is valid (never 1: one model reviewing alone is not a board).

One GO provider is not a dead end: to reach the two-seat minimum, offer the documented fallbacks: the same provider in multiple seats with different lenses, a local `ollama` seat (never egresses), or a human seat (`references/board-composition.md`).

Before launch, show the full **seat → provider → lens** table:

- Up to the preset's lens count, lenses auto-assign positionally.
- Past that, propose distinct additional lenses (drawn from other presets or composed per `references/lens-presets.md` §Custom lenses) for the user to accept or edit.
- The same lens on two **different** providers is allowed and often the point: a cross-model comparison on one axis. The same provider carrying the same lens twice is not; make each duplicate-provider seat differ by lens.
- Warn on cost before a big board: seats × rounds at high effort is the multiplier, and a 10-seat deep run takes serious time and tokens (`--dry-run` estimates).

## Step 4: Reasoning depth

Reuse approved effort. When unresolved, offer **Highest available** (the default: Claude `fable` at `max`, Codex `xhigh`, Gemini highest thinking, Grok `high`) / **Standard** / **Quick**, resolved through the `--tier` machinery (`SKILL.md` §Core Defaults). Note that any single seat can be overridden on request; don't table every seat unless asked.

## Step 5: Rounds and output

Rounds (`1`/`2`/`3`/`auto`: Formal Board Review only; the other modes fix their own phases), cross-reading, and output shape (`quick verdict` / `full handoff` / `implementation sequence`), each with the default marked.

On a Competitive run, offer the optional graft-and-verify close here (`references/modes.md` §Competitive), off by default and marked as such. Name the cost on the card: it adds a synthesis pass, a per-graft endorsement vote, and a verification pass on top of the three phases; and note that a wildly divergent field ends in a recommendation to reframe and re-run, a fresh tournament at full cost that only launches through this intake again.

## Step 6: Confirm-summary, then consent

Show the resolved plan before launch: mode, any optional phases, seats and lenses, effort, rounds, output, costs, and artifact location. Reuse an existing explicit approval of this same plan; otherwise obtain it. Build defaults from authorized GO seats, resolve unavailable seats, and keep the two-seat minimum. A changed provider, expanded data scope, or materially increased cost needs its applicable authorization before launch.

Data-handling authorization (`references/data-handling.md`) remains required for non-public material: disclose what leaves the machine and to which providers. Reuse an explicit grant only for that same data and recipient scope; a generic defaults choice does not supply it.

## Done when

- Authorized preflight ran for the selected seats, all launch seats are GO, and unverified versus failed candidates are distinguished. Unavailable seats were resolved or reported; only the approved selection launches.
- The user selected the mode, in the current request, a recorded plan, or an answer to the open choice.
- The seat→provider→lens table was shown and confirmed; effort, rounds, and output each got an explicit answer or the confirmed default.
- The resolved plan and any required data handling have explicit authorization, reused where the same scope was already approved.
