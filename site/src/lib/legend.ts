/**
 * The legend — a chart's key, which is what a glossary is.
 *
 * Rules this file is held to, because a reference work is only worth the
 * discipline behind it:
 *
 *  1. A definition states what a working engineer would accept, not what a
 *     vendor would like them to believe. Where a term is mostly a rebrand, the
 *     entry says so.
 *  2. `band` grades a CLAIM, never a word. "Thin" on graph engineering grades
 *     the claim that it is a distinct discipline — the underlying patterns are
 *     Established and the entry says which.
 *  3. `skill` is set only where a catalog skill genuinely implements the
 *     concept and its SKILL.md can be quoted to prove it. An aspirational
 *     mapping is worse than none.
 *  4. Every dated or numeric claim is a maintenance liability. Anything that
 *     can go stale carries enough detail to re-check it.
 */

export type Band = "established" | "emerging" | "contested" | "thin";

export const BANDS: Record<Band, string> = {
  established: "Settled. Documented by a primary source and not seriously disputed.",
  emerging: "Real practice, thin evidence. Mostly vendor-stated or reported rather than measured.",
  contested: "Practitioners actively disagree. Anyone claiming it is settled is selling something.",
  thin: "The named claim does not hold up. The entry says which claim.",
};

export type Entry = {
  /** URL slug. Stable — other people's writing links here. */
  slug: string;
  term: string;
  group: string;
  band: Band;
  /** What the band is grading, when it is not the whole term. */
  bandClaim?: string;
  /** One scannable line for the index. */
  gloss: string;
  /** The full entry. */
  definition: string;
  seeAlso?: string[];
  /** Slug of a catalog skill that implements this, proven by its SKILL.md. */
  skill?: string;
};

export type Group = {
  name: string;
  standfirst: string;
};

export const GROUPS: Group[] = [
  {
    name: "The window",
    standfirst:
      "Everything here exists because the window is fixed and nothing in it survives the session.",
  },
  {
    name: "Documents an agent reads",
    standfirst:
      "A document an agent reads is a lever on its behaviour, not prose. These are the parts that move it.",
  },
  {
    name: "The harness",
    standfirst: "Everything around the model: what it can call, what it may do, and what it costs.",
  },
  {
    name: "How work is arranged",
    standfirst:
      "Decomposition, ownership, and who is allowed to touch which file at the same time as whom.",
  },
  {
    name: "Handing off",
    standfirst: "Getting a session's state out of a window and into something that outlives it.",
  },
  {
    name: "Verification and authority",
    standfirst:
      "Telling done from claimed-done, and naming who decides when the two disagree.",
  },
  {
    name: "Unsurveyed water",
    standfirst:
      "Terms in motion. Some name real practice, some name a naming event. The band says which.",
  },
];

export const ENTRIES: Entry[] = [
  // ── The window ─────────────────────────────────────────────────────────────
  {
    slug: "context-rot",
    term: "Context rot",
    group: "The window",
    band: "established",
    skill: "handoff",
    gloss: "Recall degrades as input grows, even when the task stays exactly as hard.",
    definition:
      "Recall degrades as the input gets longer even when the task stays exactly as hard. Chroma held difficulty fixed and varied only the filler across 18 models and roughly 194,000 calls; performance fell with length in all of them. Anthropic describes it as a gradient rather than a cliff. The working consequence is that a window has a useful capacity well below its stated one — which is why this catalog's handoff triggers at half.",
    seeAlso: ["compaction", "progressive-disclosure", "handoff-artifact"],
  },
  {
    slug: "compaction",
    term: "Compaction",
    group: "The window",
    band: "established",
    skill: "handoff",
    gloss: "Summarising a full conversation and restarting. Selection is the hard part.",
    definition:
      "Summarising a conversation that is nearing the window limit and restarting in a fresh one. The hard part is selection: what gets kept and what gets discarded. The corollary engineers keep relearning expensively is that conversation is exactly what compaction eats, so anything load-bearing has to live in a file the agent will read back.",
    seeAlso: ["context-rot", "handoff-artifact", "agents-md"],
  },
  {
    slug: "progressive-disclosure",
    term: "Progressive disclosure",
    group: "The window",
    band: "established",
    skill: "writing-for-agents",
    gloss: "Load detail in tiers, so only the branch actually reached gets paid for.",
    definition:
      "Loading detail in tiers, so only what a branch actually reaches gets loaded. The Agent Skills format quantifies it: name and description (about 100 tokens) at startup, the SKILL.md body on activation, bundled scripts and references only when required. It is not primarily a token optimisation — it is how the top of a document stays legible.",
    seeAlso: ["context-pointer", "agent-skill", "context-load"],
  },

  // ── Documents an agent reads ───────────────────────────────────────────────
  {
    slug: "context-pointer",
    term: "Context pointer",
    group: "Documents an agent reads",
    band: "emerging",
    skill: "writing-for-agents",
    gloss: "A reference the agent holds, naming material it does not — plus when to go get it.",
    definition:
      "A reference the agent already holds that names material it does not, plus the condition for going to get it. A skill's description is one; a line in AGENTS.md naming a doc is the same object. The pointer's wording, not its target, decides whether the agent reaches the material — a must-have document behind a weakly worded pointer is a variance bug, and the fix is sharper wording before inlining anything.",
    seeAlso: ["progressive-disclosure", "leading-word", "no-op"],
  },
  {
    slug: "leading-word",
    term: "Leading word",
    group: "Documents an agent reads",
    band: "emerging",
    skill: "writing-for-agents",
    gloss: "A pretrained concept the agent thinks with — frontier, fog, tracer bullet, lane.",
    definition:
      "A compact concept already living in the model's pretraining that the agent thinks with while running a document — frontier, fog, tracer bullet, lane. Repeated as a token and never as a sentence, it accumulates a distributed definition and anchors a whole region of behaviour cheaply, by recruiting priors the model already holds. Coining your own works only if you define it, and you pay in definition tokens what a pretrained word gives free.",
    seeAlso: ["frontier", "fog", "tracer-bullet", "lane"],
  },
  {
    slug: "context-load",
    term: "Context load / cognitive load",
    group: "Documents an agent reads",
    band: "emerging",
    skill: "writing-for-agents",
    gloss: "Two budgets most writing collapses into one. Only the first should be minimised.",
    definition:
      "Two budgets that most prompt-engineering writing collapses into one. Context load is always-loaded material occupying the window, paid in tokens and attention. Cognitive load is the cost on the human of knowing which documents exist and when to reach for each. The second is not a cost to minimise: it is the price of human agency, spent where judgment matters and removed where it does not.",
    seeAlso: ["context-pointer", "progressive-disclosure"],
  },
  {
    slug: "no-op",
    term: "No-op",
    group: "Documents an agent reads",
    band: "emerging",
    skill: "writing-for-agents",
    gloss: "An instruction the model already obeys. It pays load to say nothing.",
    definition:
      "An instruction the model already obeys by default. It pays load to say nothing. The test — does this change behaviour versus the default? — is model-relative rather than reader-relative, so two people arguing about a no-op are arguing about the default and settle it by running the document, not by debating it. When a sentence fails the test, delete the sentence rather than trimming words out of it. Related and often confused: predictable means the agent takes the same process every run, not that it produces the same output.",
    seeAlso: ["context-pointer", "completion-criterion", "context-load"],
  },
  {
    slug: "completion-criterion",
    term: "Completion criterion",
    group: "Documents an agent reads",
    band: "emerging",
    skill: "writing-for-agents",
    gloss: "What tells an agent the work is finished. Vague bounds invite premature completion.",
    definition:
      "The condition that tells an agent the work is finished. Clarity decides whether it can tell done from not-done; demand decides how much digging it does on the way there. A vague bound invites premature completion — ending early as attention drifts toward being done. The strongest criteria are both checkable and exhaustive; in this catalog they surface as the “Done when (checkable)” section every skill carries.",
    seeAlso: ["no-op", "verification-gate", "self-reported-green"],
  },
  {
    slug: "agents-md",
    term: "AGENTS.md",
    group: "Documents an agent reads",
    band: "established",
    skill: "setup",
    gloss: "A README for agents. Plain markdown, no schema, closest thing to a neutral convention.",
    definition:
      "A README for agents: a predictable place for the context and instructions a coding agent needs, kept separate from README.md because that one is for humans. No schema — it is plain markdown. Nested files are supported, with the closest file to the edited file winning and explicit user instructions overriding everything. Reported across 60,000-plus projects and now stewarded under the Linux Foundation's Agentic AI Foundation, it is the closest thing agentic coding has to a genuinely vendor-neutral convention.",
    seeAlso: ["agent-skill", "compaction", "context-pointer"],
  },
  {
    slug: "agent-skill",
    term: "Agent Skill (SKILL.md)",
    group: "Documents an agent reads",
    band: "established",
    gloss: "A folder of instructions an agent loads on demand. The portability is real.",
    definition:
      "An organised folder of instructions, scripts and resources an agent discovers and loads on demand. At minimum a directory containing a SKILL.md with YAML frontmatter; only name and description are required. Introduced by Anthropic in October 2025 and published as an open standard that December. The portability is real, not marketing: a skill using only name, description and plain markdown runs unchanged across Claude Code, Codex, Cursor and others. Note that the skill is portable and the plugin wrapper around it is not.",
    seeAlso: ["progressive-disclosure", "agents-md", "hook"],
  },

  // ── The harness ────────────────────────────────────────────────────────────
  {
    slug: "subagent",
    term: "Subagent",
    group: "The harness",
    band: "established",
    skill: "grilling",
    gloss: "A delegated worker in its own window, returning a summary rather than its transcript.",
    definition:
      "A delegated worker running in its own context window with its own system prompt and tool allowlist, returning a summary rather than its transcript. The economics are the point: it may burn tens of thousands of tokens and hand back one or two thousand. The everyday trigger is simple — reach for one when a side task would flood the main conversation with search results, logs or file contents nobody will reference again.",
    seeAlso: ["orchestrator", "lane", "teammate"],
  },
  {
    slug: "mcp",
    term: "MCP (Model Context Protocol)",
    group: "The harness",
    band: "established",
    gloss: "Open standard for connecting agents to external systems. The window cost is real.",
    definition:
      "An open standard for connecting AI applications to external systems — data, tools, prompts — implemented by Claude, ChatGPT, VS Code, Cursor and many others, so a server built once integrates everywhere. Adoption is its strongest argument. The cost vendor material omits is real: most clients load every tool definition up front, so descriptions occupy the window before any work starts, and every intermediate result round-trips through the model. Install servers casually and you pay that tax on every single turn.",
    seeAlso: ["hook", "prompt-injection", "prompt-caching"],
  },
  {
    slug: "hook",
    term: "Hook",
    group: "The harness",
    band: "established",
    gloss: "A shell command the harness runs at a fixed point. Exit codes are the interface.",
    definition:
      "A shell command the harness runs at a fixed point in the agent's loop — not a request to the model. Exit codes are the interface: a non-zero exit can block the transition the hook fired on. It is the only lever on this page the model cannot argue with, which is also why an untrusted repository that can write a hook has execution on your machine. The distinction worth holding: an instruction is obeyed by disposition, a hook is enforced by the harness.",
    seeAlso: ["verification-gate", "worktree-isolation", "self-reported-green"],
  },
  {
    slug: "permission-level",
    term: "Permission level",
    group: "The harness",
    band: "established",
    gloss: "How much the agent may do without asking. A blast-radius control, not a correctness one.",
    definition:
      "How much the agent may do without asking: plan-only, per-tool allowlist, auto-accept, no prompts. It is a blast-radius control, not a verification control — raising it does not make the work more correct, only less interrupted. This is the setting people change most often and reason about least. Pair every step up with a gate that does not depend on the model's own account of itself.",
    seeAlso: ["hook", "verification-gate", "worktree-isolation"],
  },
  {
    slug: "prompt-caching",
    term: "Prompt caching",
    group: "The harness",
    band: "established",
    gloss: "Reuse of a processed prefix. Makes the front of a context expensive to change.",
    definition:
      "Reuse of an already-processed context prefix, billed at a fraction of fresh input. It makes the front of a context expensive to change and the back cheap to extend, which is why appending to a file the agent has already read costs less than rewriting its top. Most of the advice about keeping instructions stable is really an economic argument wearing a quality costume.",
    seeAlso: ["mcp", "context-load", "handoff-artifact"],
  },
  {
    slug: "prompt-injection",
    term: "Prompt injection",
    group: "The harness",
    band: "established",
    skill: "advisory-board",
    gloss: "Agents compromised through the content they exist to process. No malware required.",
    definition:
      "The structural security problem of agentic coding: agents are compromised through the content they are designed to process. A sentence in a retrieved page, a code comment, or a tool description can redirect behaviour with no malware and no stolen credentials. Anthropic states the skills version plainly — a skill ships both instructions and code, so a malicious one can direct an agent to exfiltrate data. Install from sources you trust and read the bundled files. Be sceptical of vulnerability percentages: one audit found roughly a 78% false-positive rate from YARA-based MCP scanners, and much of the loudest coverage comes from vendors selling the cure.",
    seeAlso: ["mcp", "hook", "couldnt-verify"],
  },
  {
    slug: "agentic-search",
    term: "Agentic search vs. semantic index",
    group: "The harness",
    band: "contested",
    gloss: "Grep on demand or embed the repo. Genuinely unsettled — treat certainty as a tell.",
    definition:
      "The live architectural disagreement in code retrieval. Claude Code does not index or embed; it greps on demand, citing precision, freshness, simplicity and privacy. Cursor indexes with tree-sitter chunking, embeddings and Merkle-tree sync, and now publishes hybrid results. Genuinely unsettled — treat anyone claiming otherwise as selling something. The framing that survives scrutiny: exact search wins when you know the string, structural navigation wins for relationships, large-context stuffing wins when the repo fits, and pure vector retrieval rarely wins on code alone.",
    seeAlso: ["code-knowledge-graph", "context-rot"],
  },

  // ── How work is arranged ───────────────────────────────────────────────────
  {
    slug: "task-graph",
    term: "Task graph (dependency graph)",
    group: "How work is arranged",
    band: "established",
    skill: "to-tickets",
    gloss: "Nodes and edges recording what blocks what. The useful part is the edge, not the diagram.",
    definition:
      "Work decomposed into nodes with edges recording what blocks what, so independent nodes can run concurrently and dependent ones cannot start early. The idea is not new — LangGraph's StateGraph, AutoGen's GraphFlow, Google ADK and Anthropic's December 2024 orchestrator-workers pattern all predate the 2026 name for it. The useful part is the edge, not the diagram: a graph you drew but never enforced is a picture. Enforcement means native edges, and it comes with a disjointness rule most teams learn the hard way — an item blocked purely by edges must never also carry a “blocked” label, which is reserved for blockers that are not tracker items: a vendor gate, a scheduling constraint, a pending adjudication. A stale label is a phantom edge.",
    seeAlso: ["frontier", "graph-engineering", "issue-as-spec"],
  },
  {
    slug: "frontier",
    term: "Frontier",
    group: "How work is arranged",
    band: "established",
    skill: "grilling",
    gloss: "The nodes whose prerequisites are all satisfied — the edge of what is takeable now.",
    definition:
      "The set of nodes whose prerequisites are all satisfied — the edge of what is takeable now. On a tracker that is items which are ready-labelled, unassigned, and blocked neither by a dependency edge nor by a label. In an interview it is every decision whose prerequisites are already settled. Same word, same meaning, two surfaces. An empty frontier is a fact that needs a reason attached — all claimed, triage stalled, or everything blocked — because an empty answer with no breakdown sends people guessing.",
    seeAlso: ["task-graph", "fog", "claim"],
  },
  {
    slug: "fog",
    term: "Fog",
    group: "How work is arranged",
    band: "emerging",
    skill: "decision-map",
    gloss: "Work whose open questions gate each other. Density picks the instrument.",
    definition:
      "Work whose open questions gate each other, so nobody can spec it in one sitting. Fog density picks the instrument: deep fog gets a ticket per question, resolved most-gating-first; shallow fog gets a single sitting. The move most teams skip is the no-fog exit — when the survey finds every question answerable from what already exists, stop and write an ordinary spec. A map with nothing undecided is overhead, not planning.",
    seeAlso: ["frontier", "leading-word", "the-decider"],
  },
  {
    slug: "tracer-bullet",
    term: "Tracer bullet",
    group: "How work is arranged",
    band: "established",
    skill: "to-tickets",
    gloss: "A thin slice all the way through, not a layer that goes nowhere alone.",
    definition:
      "A thin slice that goes all the way through the system rather than a horizontal layer that goes nowhere alone. Hunt and Thomas's term, and explicitly not a prototype: prototyping generates disposable code, while tracer code is lean but complete and forms part of the final skeleton. Three tests: verifiable alone, PR-sized, ordered by what it unblocks. “Build the data layer” fails all three, because its acceptance criteria are always someone else's.",
    seeAlso: ["issue-as-spec", "task-graph", "spec-driven-development"],
  },
  {
    slug: "issue-as-spec",
    term: "Issue-as-spec",
    group: "How work is arranged",
    band: "emerging",
    skill: "to-tickets",
    gloss: "The work item's body is the spec. Ready means a stranger could take it.",
    definition:
      "The work item's body is the spec — destination, acceptance criteria, out of scope — written once on the tracker before any code. The implementing brief adds standing constraints and mechanics, never a second copy of the requirements, and the work summary posts back to the item so the tracker stays the durable record. The readiness bar is a handoff test: an item is ready only when its body could be handed to a stranger.",
    seeAlso: ["tracer-bullet", "spec-driven-development", "task-graph"],
  },
  {
    slug: "lane",
    term: "Lane",
    group: "How work is arranged",
    band: "emerging",
    skill: "orchestrate",
    gloss: "One session, one workspace, one branch, exactly one work item.",
    definition:
      "A working session — agent or human — in its own workspace on its own branch, holding exactly one work item. Lanes commit on their branch and stop; integration belongs to whoever routed them. The vocabulary is not standardised: other systems say teammate, worker, or agent. What is standard is the constraint underneath it — two workers editing one file leads to overwrites, so the work has to be broken up until each owns a different set of files.",
    seeAlso: ["orchestrator", "teammate", "claim", "worktree-isolation"],
  },
  {
    slug: "teammate",
    term: "Teammate (agent teams)",
    group: "How work is arranged",
    band: "emerging",
    gloss: "The vendor word for a lane, with the mechanics shipped. Guidance is three to five.",
    definition:
      "The vendor's name for what this catalog calls a lane, with the coordination mechanics shipped rather than improvised: pending tasks whose dependencies are unresolved cannot be claimed, claims lock files, and each teammate has a mailbox. The documentation's own guidance is three to five, and it names dependency-heavy or same-file work as the wrong fit — which is the same constraint the lane entry states, arrived at independently.",
    seeAlso: ["lane", "orchestrator", "subagent"],
  },
  {
    slug: "claim",
    term: "Claim (read-before-write)",
    group: "How work is arranged",
    band: "emerging",
    skill: "setup",
    gloss: "Record ownership before touching anything, in a form a machine can read.",
    definition:
      "Recording ownership of a work item before touching it, in a form a machine can read. An assignee field alone cannot distinguish two sessions sharing one account, so the claim is a comment marker a scanner can match. Taking over requires evidence that the previous lane is dead, and death is hard to prove: an agent session can be alive but between turns, invisible to every process probe. No processes and no commits is not evidence.",
    seeAlso: ["lane", "frontier", "stale-next-rule"],
  },
  {
    slug: "orchestrator",
    term: "Orchestrator",
    group: "How work is arranged",
    band: "emerging",
    skill: "orchestrate",
    gloss: "Routes work, audits results, owns integration, never implements.",
    definition:
      "One session that routes work into lanes, audits what comes back, owns integration, and never implements. The rules that make it work are the non-obvious ones: exactly one live orchestrator at a time, because two of them routing the same board is the same collision class as two sessions building the same item; delegation moves the executor and never the standard; and context is the orchestrator's scarcest resource, which makes delegation a context-preservation technique before it is a throughput one.",
    seeAlso: ["lane", "subagent", "self-reported-green", "the-decider"],
  },
  {
    slug: "worktree-isolation",
    term: "Worktree isolation",
    group: "How work is arranged",
    band: "established",
    gloss: "Separate directories over one object store. Not a security boundary.",
    definition:
      "Giving each parallel agent its own checked-out directory over one shared object store. It works for what it claims — separate files, separate branches, no lock contention — and it is not a security boundary, which is the half nobody repeats. Object store, refs, config, stash and hooks all resolve to the shared common directory, so an agent inside a worktree can install a pre-commit hook that runs as you on your next commit. The usual objection to cloning instead — that it is slow — does not hold at the repository sizes anyone here works at. Worktree when a person drives; clone when something else does.",
    seeAlso: ["lane", "hook", "claim"],
  },

  // ── Handing off ────────────────────────────────────────────────────────────
  {
    slug: "handoff-artifact",
    term: "Handoff artifact",
    group: "Handing off",
    band: "emerging",
    skill: "handoff",
    gloss: "One small file so a fresh session resumes with no re-explanation. Overwrite, never append.",
    definition:
      "One small file capturing where the work stands, so a fresh session resumes with no re-explanation. Written at roughly half the window rather than when it fills, because the oldest details fall away and long-chain reasoning degrades before the hard limit is ever reached. Two rules keep it useful: overwrite rather than append, since an appended handoff decays into a transcript nobody reads; and stay a pointer rather than a transcript, linking the durable records instead of copying them.",
    seeAlso: ["stale-next-rule", "compaction", "context-rot"],
  },
  {
    slug: "stale-next-rule",
    term: "Stale-NEXT rule",
    group: "Handing off",
    band: "emerging",
    skill: "handoff",
    gloss: "A handoff points at the query and never enumerates items. Lists go stale on claim.",
    definition:
      "A handoff points at the tracker query and never enumerates work items. A listed item number goes stale the moment another session claims it, and a session starting from that list collides with the claimer. The corollary is the part people skip: reading a handoff never authorises starting an item — the claim runs first. It is the clearest example on this page of why you defer to a live graph instead of snapshotting one.",
    seeAlso: ["handoff-artifact", "claim", "frontier"],
  },

  // ── Verification and authority ─────────────────────────────────────────────
  {
    slug: "verification-gate",
    term: "Verification gate",
    group: "Verification and authority",
    band: "established",
    skill: "orchestrate",
    gloss: "A check the model cannot argue past, because the harness enforces it.",
    definition:
      "A check the model cannot argue its way past, because the harness enforces it rather than the model. Task and idle hooks that block a transition on a non-zero exit are one shape; pre-commit hooks and required CI checks are the same shape. Prefer deterministic graders where you can get them: a validator can prove a field is missing, where a model can only argue that its work is complete.",
    seeAlso: ["hook", "oracle", "self-reported-green", "llm-as-judge"],
  },
  {
    slug: "oracle",
    term: "Oracle",
    group: "Verification and authority",
    band: "established",
    gloss: "An independent source of truth about correctness. Its presence predicts more than topology.",
    definition:
      "An independent source of truth that can say whether an output is correct without a human reading it: a reference implementation, a differential comparison against a known-good tool, a property test, a type checker. The presence or absence of an oracle predicts more about how well agents do on a task than any topology or prompt does. Where one exists, verification is cheap and parallelism is safe. Where none exists, every gate on this page degrades into a model arguing that it is finished.",
    seeAlso: ["verification-gate", "llm-as-judge", "agentic-engineering", "self-reported-green"],
  },
  {
    slug: "self-reported-green",
    term: "Self-reported green",
    group: "Verification and authority",
    band: "established",
    skill: "orchestrate",
    gloss: "A claim that verification passed, offered instead of evidence. Re-run it.",
    definition:
      "An agent's claim that verification passed, offered in place of evidence. Re-run it. Require per-command exit codes with zero skipped checks, and remember that piped output is not evidence: a pipeline reports the last command's status, so any command followed by <code>tail</code> reads green whenever <code>tail</code> does. This is a bug most teams have shipped at least once, usually in CI, usually for months.",
    seeAlso: ["verification-gate", "oracle", "orchestrator"],
  },
  {
    slug: "llm-as-judge",
    term: "LLM-as-judge",
    group: "Verification and authority",
    band: "established",
    bandClaim:
      "Established as a technique with well-documented biases — not as a substitute for a deterministic gate.",
    skill: "advisory-board",
    gloss: "A model grading a model. Standard, biased, and worst exactly when candidates are close.",
    definition:
      "Using a model to grade another model's output against a rubric, either as an evaluation or as an inline gate. Now standard and economically viable, with limitations severe enough that any honest description leads with them: position and presentation bias can move accuracy by more than ten points on code evaluation specifically, and it is worst exactly when candidates are close in quality; scores run systematically optimistic. Treat judges as signal and deterministic checks as gates.",
    seeAlso: ["verification-gate", "oracle", "adversarial-review", "echo-risk"],
  },
  {
    slug: "adversarial-review",
    term: "Adversarial review",
    group: "Verification and authority",
    band: "emerging",
    skill: "advisory-board",
    gloss: "Several reviewers with different lenses, rather than one working sequentially.",
    definition:
      "Running several reviewers with deliberately different lenses, or several investigators told to disprove each other, rather than one reviewer working sequentially. The rationale is anchoring: once one theory is explored, later investigation bends toward it, and a single reviewer gravitates to one class of issue at a time. The mechanism is sound and cheap to try. The supporting evidence is vendor-stated rather than benchmarked, and nobody should pretend otherwise.",
    seeAlso: ["echo-risk", "couldnt-verify", "llm-as-judge"],
  },
  {
    slug: "echo-risk",
    term: "Echo risk",
    group: "Verification and authority",
    band: "emerging",
    skill: "advisory-board",
    gloss: "Agreement between models is not automatically evidence.",
    definition:
      "Agreement between models is not automatically evidence. Convergence is earned when reviewers reached the same answer independently, and social when they read each other and drifted into agreement. The distinction is measurable in a crude way — verdict flips toward the majority, overlapping citation sets, self-reported deference — and worth measuring, but the honest claim is narrow: it flags possible echo, it does not prove independence. High overlap can be an honest read of a small source.",
    seeAlso: ["adversarial-review", "couldnt-verify", "llm-as-judge"],
  },
  {
    slug: "couldnt-verify",
    term: "Couldn't-verify",
    group: "Verification and authority",
    band: "emerging",
    skill: "advisory-board",
    gloss: "An explicit bucket for what a review leaned on but did not check.",
    definition:
      "An explicit bucket for claims a review leaned on but did not check, plus the blind spots no reviewer could see. It is the main guard against a confident, unanimous, wrong answer, because several models can converge on the same missing fact. Its sharper cousin: a verified citation means the receipt resolves — the cited line exists and the quoted text is there — not that the inference drawn from it is sound. The gate catches fabrication, not grounded-but-wrong reasoning.",
    seeAlso: ["echo-risk", "adversarial-review", "prompt-injection"],
  },
  {
    slug: "the-decider",
    term: "The decider",
    group: "Verification and authority",
    band: "emerging",
    skill: "setup",
    gloss: "The named person who adjudicates. Always asked, never inferred.",
    definition:
      "The named person who adjudicates decisions in a repo: always asked, never inferred. It is the one role every skill in this catalog defers to, and binding it to an actual name is the first thing setup does. The failure it prevents is specific and common — an agent that answers its own questions has produced nothing but a transcript of itself.",
    seeAlso: ["fog", "orchestrator", "adversarial-review"],
  },

  // ── Unsurveyed water ───────────────────────────────────────────────────────
  {
    slug: "graph-engineering",
    term: "Graph engineering",
    group: "Unsurveyed water",
    band: "thin",
    bandClaim:
      "The band grades the claim that this is a distinct discipline. The underlying patterns are Established — see Task graph.",
    gloss: "A 2026 name for task-graph orchestration. The patterns predate it by 19 months.",
    definition:
      "As used since July 2026, a name for task-graph orchestration: decompose a goal into a dependency graph, run independent nodes concurrently, gate integration behind completed prerequisites. A separate community uses the same words for code knowledge graphs, and the two have nothing to do with each other. The patterns are real and Anthropic documented them in December 2024 without ever using the word “graph”; no comparative benchmark for the labelled version exists. The advocacy literature concedes it outright: “Calling the practice graph engineering is a naming event, not a technical one.”",
    seeAlso: ["task-graph", "loop-engineering", "code-knowledge-graph", "orchestrator"],
  },
  {
    slug: "loop-engineering",
    term: "Loop engineering",
    group: "Unsurveyed water",
    band: "emerging",
    gloss: "Designing the system that prompts the agent, instead of prompting it yourself.",
    definition:
      "Designing the system that prompts the agent instead of prompting it yourself. Named by Addy Osmani on 7 June 2026; attribution is genuinely muddled, with other accounts crediting different coinages. The practice is real and the load-bearing part is the caveats, which the marketing versions drop: a loop running unattended is a loop making mistakes unattended, and “done” is a claim rather than proof.",
    seeAlso: ["graph-engineering", "verification-gate", "oracle"],
  },
  {
    slug: "agentic-engineering",
    term: "Agentic engineering",
    group: "Unsurveyed water",
    band: "emerging",
    gloss: "Directing fallible agents under human oversight. Automates what you can verify.",
    definition:
      "Andrej Karpathy's successor framing to vibe coding — the term he coined in February 2025 for accepting generated code without reading it, and later bounded rather than disowned: “Vibe coding raises the floor. Agentic engineering is about extrapolating the ceiling.” The framing is directing fallible agents under structured human oversight rather than writing the code yourself, with people in charge of the spec and the plan. The most load-bearing line is about scope: traditional computers automate what you can specify in code, and this round of models automates what you can verify — which is why capability peaks in verifiable domains.",
    seeAlso: ["oracle", "the-decider", "verification-gate"],
  },
  {
    slug: "code-knowledge-graph",
    term: "Code knowledge graph",
    group: "Unsurveyed water",
    band: "emerging",
    gloss: "Index the repo as symbols and relationships. Building it is the easy half.",
    definition:
      "Indexing a repository as symbols and relationships — call edges, imports, inheritance, tests — so an agent traverses dependencies rather than matching strings. This half has the actual evidence: RepoGraph, CodexGraph, LocBench results, and a controlled three-arm study reporting a localisation gain within a harness and no regression against agentic grep. The finding that matters most for anyone building one is behavioural, not technical: in CodeCompass's trials, 58% of runs with graph access made zero tool calls, and agents needed explicit prompting to use it. Building the index is the easy half.",
    seeAlso: ["agentic-search", "graph-engineering", "context-pointer"],
  },
  {
    slug: "spec-driven-development",
    term: "Spec-driven development",
    group: "Unsurveyed water",
    band: "emerging",
    skill: "to-tickets",
    gloss: "Write the spec first and generate from it. Real tooling; oversold as executable.",
    definition:
      "Writing a spec first and generating from it, rather than prompting straight to code. GitHub's spec-kit ships a real pipeline — constitution, specify, plan, tasks, implement — with a clarify step for underspecified areas and a checklist step honestly described as “unit tests for English.” Real tooling with real adoption. Be sceptical of the stronger claim that specs are literally executable, which overstates what a markdown file does; this catalog's version puts the spec in the work item instead.",
    seeAlso: ["issue-as-spec", "tracer-bullet", "fog"],
  },
];

export function byGroup(): Array<{ group: Group; entries: Entry[] }> {
  return GROUPS.map((group) => ({
    group,
    entries: ENTRIES.filter((e) => e.group === group.name),
  })).filter((g) => g.entries.length > 0);
}

export function getEntry(slug: string): Entry | undefined {
  return ENTRIES.find((e) => e.slug === slug);
}

/**
 * Every see-also must resolve, and every skill named must be in the catalog.
 * Called from the page so a broken cross-link fails `next build` rather than
 * shipping — the legend's whole value is that its links go somewhere.
 */
export function assertLegendSound(skillSlugs: string[]): void {
  const slugs = new Set(ENTRIES.map((e) => e.slug));
  const known = new Set(skillSlugs);
  const problems: string[] = [];

  for (const entry of ENTRIES) {
    for (const ref of entry.seeAlso ?? []) {
      if (!slugs.has(ref)) problems.push(`${entry.slug}: see-also "${ref}" does not exist`);
    }
    if (entry.skill && !known.has(entry.skill)) {
      problems.push(`${entry.slug}: names skill "${entry.skill}", which is not in the catalog`);
    }
    if (!GROUPS.some((g) => g.name === entry.group)) {
      problems.push(`${entry.slug}: group "${entry.group}" is not declared`);
    }
  }

  if (problems.length) throw new Error(`legend.ts:\n  ${problems.join("\n  ")}`);
}
