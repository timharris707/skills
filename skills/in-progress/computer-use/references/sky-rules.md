These rules are appended verbatim to every brief the runner sends to Codex. They
restate the installed plugin's own instructions (the `computer-use` plugin's SKILL.md
under the openai-bundled marketplace, version 1.0.1001103, read 2026-09-20: the API
types, diff behaviour, `paste` formats, xdotool key syntax, the no-global-shortcuts
note, and the automatic post-action wait all come from that file) plus the habits
that keep a run checkable.

- Observe before acting. The first call is `get_app_state({app, disableDiff: true})` for a full tree.
- Accessibility results are diffs by default. Pass `disableDiff: true` whenever you need the whole tree, and after any turn where you only looked at the screenshot.
- Every `element_index` comes from the latest `get_app_state`. After any action, call `get_app_state` again before using an index. Never reuse an index from before an action.
- Prefer element indexes over coordinates. Use `x`/`y` only when the tree exposes no usable target.
- `scroll` needs either an `element_index` or finite `x` and `y`. Without one of them it fails.
- `type_text` presses Return for every newline, which can send a message or submit a form. For multiline or formatted text use `paste({app, text, format})` with `format` set to `text`, `md`, or `html`. `paste` restores the previous clipboard afterwards.
- `drag` takes explicit start and end coordinates. Take a fresh `get_app_state` (with screenshot) immediately before the drag, and verify the result immediately after.
- `perform_secondary_action` only accepts an action name the accessibility text actually lists for that element. Never guess names like "Show Menu" or "Expand".
- `select_text` selects matching text in an editable element; use `prefix`/`suffix` to disambiguate. `set_value` replaces an editable value. Both need a fresh index.
- `press_key` and `type_text` target the named app and cannot trigger global shortcuts. Key syntax is xdotool-style: `"Return"`, `"Tab"`, `"super+c"`.
- If a call fails by display name, retry once with the bundle ID from `list_apps()`. Do not call `list_apps()` just to look up an app you were given.
- If the result says "Computer Use was not approved to use <app>", stop immediately and reply `blocked` with that exact text. Do not try another app.
- The runtime already waits after an action before capturing state; do not add sleeps.
- A screenshot alone does not prove a change that is only visible in accessibility text. Read the text.
- Screenshot URLs arrive as `file://` (possibly percent-encoded) or as data URLs. Put them in `evidence` as received, minus the `file://` prefix.
