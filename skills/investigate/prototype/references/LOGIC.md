# Logic prototype branch

Answer "does this state model / logic feel right" by pushing a candidate machine through the cases that are hard to reason about on paper, behind a small interactive shell.

## Build

1. **The candidate module is PURE** — pure-domain discipline from birth: no I/O, no database, no clock reads inside the logic; in-memory state only; explicit inputs, explicit transitions, typed refusals. Write it as if it will lift into the repo's domain layer, because the validated version will.
2. **Pick the shell. It imports the module; nothing flows back.** Either shape is disposable, and all experiment code stays on the `prototype/<name>` branch.
   - **Terminal UI** — the default when the decider drives it with you in-session. A readline/keypress loop is enough: it renders the machine's state, offers its transitions, and lets you drive edge sequences interactively — an event landing mid-transition, a refusal after a partial step, an out-of-order input.
   - **Single shareable HTML file** — when the reviewer is a non-developer (a designer, a PM, a domain expert) or the demo must travel. One self-contained file — no framework, no bundler, no server; it opens by double-click and survives being emailed around. It renders the full state as a readable panel after every action, offers free-play buttons (one per transition), and carries guided walkthroughs for the awkward scenarios, everything labeled in domain language rather than the code's.
3. **Chase the paper-hard cases.** Script the sequences the discussion could not settle and drive them live; when a transition surprises you, that surprise is the finding — record it.

## After validation

The validated reducer/machine lifts into the repo's domain layer **through a normal change**, where real tests and the repo's invariant discipline pin it (the prototype's runs are design evidence, not test coverage). The prototype branch stays as the reference for that work. Then return to [SKILL.md](../SKILL.md) "Done when".
