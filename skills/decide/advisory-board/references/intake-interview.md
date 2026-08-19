# Guided Intake: the wizard

Every board run opens with this intake. It is **mandatory**: the run's shape is chosen by the user on the record, never by the agent on the user's behalf: mode, seats, lenses, effort, rounds, output. The one fast path is `use defaults`, which collapses steps 2-5 into a single confirm-summary card (step 6); it never skips step 1, it never collapses below two GO seats (step 3's fallbacks are the user's call), it never skips confirmation, and it never waives data-handling consent.

Present choices the way the `grilling` skill does: choice-shaped questions as selection cards with your recommendation first and marked `(Recommended)`, at most four cards per round; open questions as ❓/➡️ text. Where cards aren't available, ask the same questions as numbered text.

## Step 1: Doctor first

Run `run_board.py doctor` (or the manual preflight, `references/preflight.md`) before proposing anything. Never offer the user a seat you have not confirmed is GO today.

Report per-seat status in plain terms, e.g. `grok: installed but not logged in` or `gemini: CLI missing`, and for each broken seat offer exactly three choices:

- **Fix it now.** With the user's yes, run the install/update via `run_board.py toolchain --install/--update`. Authentication is always the user's hands: print the auth command, wait, then re-probe. Never install or update anything without a yes on the card.
- **Continue without it.** The board proceeds smaller; the missing seat is named in the run plan.
- **Abort.** Stop cleanly.

## Step 2: Goal, then mode

Ask for the goal in the user's own words (❓ text, not a card), then classify it into an intent and recommend a mode from the table in `references/modes.md` §Choosing a mode. Show the recommendation as a card with the other two modes and their one-liners beside it: the user picks; a goal never silently implies a mode.

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

One card: **Highest available** (the default: Claude `fable` at `max`, Codex `xhigh`, Gemini highest thinking, Grok `high`) / **Standard** / **Quick**, resolved through the `--tier` machinery (`SKILL.md` §Core Defaults). Note that any single seat can be overridden on request; don't table every seat unless asked.

## Step 5: Rounds and output

Rounds (`1`/`2`/`3`/`auto`: Formal Board Review only; the other modes fix their own phases), cross-reading, and output shape (`quick verdict` / `full handoff` / `implementation sequence`), each with the default marked.

On a Competitive run, offer the optional graft-and-verify close here (`references/modes.md` §Competitive), off by default and marked as such. Name the cost on the card: it adds a synthesis pass, a per-graft endorsement vote, and a verification pass on top of the three phases; and note that a wildly divergent field ends in a recommendation to reframe and re-run, a fresh tournament at full cost that only launches through this intake again.

## Step 6: Confirm-summary, then consent

Play back the fully resolved plan as one card the user approves before anything runs: mode (on Competitive, with `graft-and-verify close: on/off` as resolved), seats with lenses, effort, rounds, output, and where artifacts land. **Nothing launches without this yes.** `use defaults` reaches this card only through step 1: run doctor first, resolve each broken seat with the user (fix, continue without, or abort), and only then resolve steps 2-5 to defaults and build this card from what doctor confirmed. A seat that is not GO never appears on the card as a default, and below two GO seats defaults cannot fill the board: walk step 3's fallbacks with the user before this card (`references/board-composition.md` sets the two-seat minimum).

Data-handling consent (`references/data-handling.md`) is separate and unwaivable: for non-public material, disclose what leaves the machine and to whom, and get the explicit go-ahead; `use defaults` and the confirm-summary never cover it.

## Done when

- Doctor ran and every offered seat was GO (or the user chose fix/continue/abort per broken seat).
- The user picked the mode from a recommendation card; the agent never selected it for them.
- The seat→provider→lens table was shown and confirmed; effort, rounds, and output each got an explicit answer or the confirmed default.
- The confirm-summary got a yes, and data-handling consent (where required) got its own yes.
