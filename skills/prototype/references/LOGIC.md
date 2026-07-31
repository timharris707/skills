# Logic prototype branch

Answer "does this state model / logic feel right" by building a tiny interactive terminal app that pushes a candidate machine through the cases that are hard to reason about on paper.

## Build

1. **The candidate module is PURE** — pure-domain discipline from birth: no I/O, no database, no clock reads inside the logic; in-memory state only; explicit inputs, explicit transitions, typed refusals. Write it as if it will lift into the repo's domain layer, because the validated version will.
2. **The terminal shell imports the module; nothing flows back.** The shell is disposable (a readline/keypress loop is enough): it renders the machine's state, offers its transitions, and lets you drive edge sequences interactively — an event landing mid-transition, a refusal after a partial step, an out-of-order input. All experiment code stays on the `prototype/<name>` branch.
3. **Chase the paper-hard cases.** Script the sequences the discussion could not settle and drive them live; when a transition surprises you, that surprise is the finding — record it.

## After validation

The validated reducer/machine lifts into the repo's domain layer **through a normal change**, where real tests and the repo's invariant discipline pin it (the prototype's terminal runs are design evidence, not test coverage). The prototype branch stays as the reference for that work. Then return to [SKILL.md](../SKILL.md) "Done when".
