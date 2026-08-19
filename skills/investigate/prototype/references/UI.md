# UI prototype branch

Answer "how should it look / behave" by mounting **three structurally different variants on the LIVE route** and letting the decider react to real renders over real data.

## Build

1. **Live route first.** Mount the variants on the actual route behind a `?variant=` query param: real shell, real data, real navigation. This is the honest representation of how the code will work; a throwaway route is the last resort, only when the live route structurally cannot host the experiment.
2. **Three variants, structurally different.** Each variant encodes a different layout / information hierarchy, a different answer to the design question. Recolors and spacing tweaks are iteration feedback, never a variant. Name them A/B/C; iteration mints D, E… encoding the feedback so far.
3. **Floating switcher pill**, dev-gated: render it only in development builds, floating over the page, showing the active variant, with `←`/`→` cycling variants. The default (no `?variant=`) renders the route exactly as the default branch does.
4. **Variants are READ-ONLY.** Every control that would mutate points at a stub (local state, a no-op handler with a visible "prototype" affordance), never at a real writer. The question is layout and behavior; real mutations belong to the real implementation.
5. Use the repo's shared design system inside every variant: the question is structure, and off-system styling makes the winner unshippable as observed.

## Visual-regression baselines stay clean

If the repo runs visual-regression baselines, they must never snapshot a variant: variants are `?variant=`-param-gated and no baseline spec passes that param, so baselines see the default route only. Keep it that way: add no prototype spec files, and leave the visual suite untouched. If a baseline changes on the prototype branch, the default render leaked variant code: fix the gate.

## Iterate

Walk each variant with the decider (or record a walkthrough for async reaction). Collect concrete reactions ("search box from A, layout from C"), encode them into the next variant, repeat until one render answers the question. Then return to [SKILL.md](../SKILL.md) "Done when".
