# Design vocabulary — depth, seams, locality, the deletion test

The shared language every codebase-review finder and the skeptic speak. Use these terms exactly — "component," "service," "API," and "boundary" each blur a distinction this vocabulary keeps sharp, and consistent language is what lets one run's claims be weighed against another's.

**Module** — anything with an interface and an implementation: a function, a class, a package, a tier-spanning slice. Deliberately scale-agnostic, so a claim about depth works at any size.

**Interface** — everything a caller must know to use the module correctly: the type signature, plus invariants, ordering constraints, error modes, required configuration, performance characteristics. Wider than "API" or "signature," which name only the type-level surface.

**Depth** — leverage at the interface: how much behavior a caller (or a test) exercises per unit of interface they must learn. A module is **deep** when a lot of behavior sits behind a small interface, **shallow** when the interface is nearly as complex as the implementation. Depth is a property of the interface, not the implementation — a deep module may be internally composed of small swappable parts; they just aren't part of the interface.

**Seam** *(Michael Feathers)* — a place where behavior can be altered without editing in that place; where a module's interface lives. Where the seam goes is its own design decision, distinct from what sits behind it. One adapter at a seam means the seam is hypothetical; two adapters make it real — a seam nothing varies across is interface paid for nothing.

**Locality** — what maintainers get from depth: change, bugs, knowledge, and verification concentrate in one place instead of spreading across callers. Fix once, fixed everywhere. Its absence is the tax the review hunts: a conceptually single change that lands as edits in five files has no locality, whatever the module diagram says.

**Leverage** — what callers get from depth: more capability per unit of interface learned. One implementation pays back across N call sites and M tests. Report payoffs in locality and leverage terms — they are the two currencies a deepening buys.

**The deletion test** — imagine deleting the module. If its complexity reappears across N callers, it was earning its keep; if complexity simply vanishes, it was a pass-through — a shallow wrapper whose interface cost more than it hid. And if *nothing* reappears anywhere — no caller misses it — the code is dead. The single test grades both the shallow-modules lens (complexity vanishes) and the dead-code lens (nothing reappears).

**The interface is the test surface** — callers and tests cross the same seam. Code that can only be tested *past* its interface is the wrong shape, and that pain is evidence for the test-pain lens, not a tooling problem to work around.

## Attribution

Adapted from Matt Pocock's [`codebase-design`](https://github.com/mattpocock/skills) (MIT), which defines this vocabulary in full — including depth-as-leverage in place of Ousterhout's line-count ratio, and the one-adapter/two-adapter seam rule. This doc trims it to what codebase-review's finders need and adds the mapping onto the skill's lenses (the deletion test doing double duty for shallow modules and dead code, test-pain as an interface-shape signal).
