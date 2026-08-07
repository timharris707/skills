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
 *  5. An entry opens with a complete sentence naming the term — "X is …" —
 *     because the first sentence is what a reader skims and what an answer
 *     engine quotes, and neither should have to assemble the subject from the
 *     heading.
 *  6. `established` means "documented by a primary source", so an established
 *     entry has to carry the source. `assertLegendSound` fails the build if one
 *     does not. Where no primary source exists for the whole term, the entry
 *     narrows what the band is grading in `bandClaim` rather than implying more
 *     evidence than there is.
 */

export type Band = "established" | "emerging" | "contested" | "thin";

export const BANDS: Record<Band, string> = {
  established: "Settled. Documented by a primary source and not seriously disputed.",
  emerging: "Real practice, thin evidence. Mostly vendor-stated or reported rather than measured.",
  contested: "Practitioners actively disagree. Anyone claiming it is settled is selling something.",
  thin: "The named claim does not hold up. The entry says which claim.",
};

/** A primary source, named so a reader can go check the entry against it. */
export type Source = {
  /** How it should read on the page. Author or publisher, then what it is. */
  label: string;
  url: string;
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
  /** The full entry. Opens by naming the term. */
  definition: string;
  /** Required on `established` entries. Enforced in `assertLegendSound`. */
  sources?: Source[];
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
      "Context rot is the degradation of a model's recall as its input gets longer, even when the task stays exactly as hard. Chroma held difficulty fixed and varied only the filler across 18 models and 194,480 calls; performance fell with length in every one of them. Anthropic describes the result as a performance gradient rather than a hard cliff. The working consequence is that a window has a useful capacity well below its stated one — which is why this catalog's handoff triggers at half.",
    sources: [
      {
        label: "Chroma, Context Rot: How Increasing Input Tokens Impacts LLM Performance (14 July 2025)",
        url: "https://www.trychroma.com/research/context-rot",
      },
      {
        label: "Anthropic, Effective context engineering for AI agents",
        url: "https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents",
      },
    ],
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
      "Compaction is summarising a conversation that is nearing the window limit and reinitiating a fresh one from the summary. Anthropic calls it the first lever for long-term coherence; Claude Code's version keeps architectural decisions, unresolved bugs and implementation details while dropping redundant tool output. The hard part is selection, and Anthropic says so directly — aggressive compaction loses context whose importance only becomes clear later. The corollary engineers keep relearning expensively is that conversation is exactly what compaction eats, so anything load-bearing has to live in a file the agent will read back.",
    sources: [
      {
        label: "Anthropic, Effective context engineering for AI agents",
        url: "https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents",
      },
    ],
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
      "Progressive disclosure is loading detail in tiers, so only what a branch actually reaches gets loaded. The Agent Skills format quantifies it, and Anthropic publishes the table: name and description at startup at roughly 100 tokens per skill, the SKILL.md body under 5,000 tokens once the skill is triggered, and bundled scripts and references at no cost at all until something reads them. It is not primarily a token optimisation — it is how the top of a document stays legible.",
    sources: [
      {
        label: "Anthropic, Agent Skills overview — the three loading levels and their token costs",
        url: "https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview",
      },
      {
        label: "Anthropic, Equipping agents for the real world with Agent Skills",
        url: "https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills",
      },
    ],
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
      "A context pointer is a reference the agent already holds that names material it does not, plus the condition for going to get it. A skill's description is one; a line in AGENTS.md naming a doc is the same object. The pointer's wording, not its target, decides whether the agent reaches the material — a must-have document behind a weakly worded pointer is a variance bug, and the fix is sharper wording before inlining anything.",
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
      "A leading word is a compact concept already living in the model's pretraining that the agent thinks with while running a document — frontier, fog, tracer bullet, lane. Repeated as a token and never as a sentence, it accumulates a distributed definition and anchors a whole region of behaviour cheaply, by recruiting priors the model already holds. Coining your own works only if you define it, and you pay in definition tokens what a pretrained word gives free.",
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
      "Context load and cognitive load are two budgets that most prompt-engineering writing collapses into one. Context load is always-loaded material occupying the window, paid in tokens and attention. Cognitive load is the cost on the human of knowing which documents exist and when to reach for each. The second is not a cost to minimise: it is the price of human agency, spent where judgment matters and removed where it does not.",
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
      "A no-op is an instruction the model already obeys by default. It pays load to say nothing. The test — does this change behaviour versus the default? — is model-relative rather than reader-relative, so two people arguing about a no-op are arguing about the default and settle it by running the document, not by debating it. When a sentence fails the test, delete the sentence rather than trimming words out of it. Related and often confused: predictable means the agent takes the same process every run, not that it produces the same output.",
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
      "A completion criterion is the condition that tells an agent the work is finished. Clarity decides whether it can tell done from not-done; demand decides how much digging it does on the way there. A vague bound invites premature completion — ending early as attention drifts toward being done. The strongest criteria are both checkable and exhaustive; in this catalog they surface as the “Done when (checkable)” section every skill carries.",
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
      "AGENTS.md is a README for agents: a predictable place for the context and instructions a coding agent needs, kept separate from README.md because that one is for humans. There is no schema — it is plain markdown. Nested files are supported, and the format's own FAQ settles the precedence question in one line: the closest AGENTS.md to the edited file wins, and explicit user prompts override everything. Reported across more than 60,000 open-source projects and now stewarded by the Agentic AI Foundation under the Linux Foundation, it is the closest thing agentic coding has to a genuinely vendor-neutral convention.",
    sources: [
      {
        label: "agents.md — the format, the nesting rule, and the adoption figure",
        url: "https://agents.md/",
      },
      {
        label: "Linux Foundation, formation of the Agentic AI Foundation (9 December 2025)",
        url: "https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation",
      },
    ],
    seeAlso: ["agent-skill", "compaction", "context-pointer"],
  },
  {
    slug: "agent-skill",
    term: "Agent Skill (SKILL.md)",
    group: "Documents an agent reads",
    band: "established",
    gloss: "A folder of instructions an agent loads on demand. The portability is real.",
    definition:
      "An Agent Skill is an organised folder of instructions, scripts and resources an agent discovers and loads on demand. At minimum it is a directory containing a SKILL.md with YAML frontmatter; only name and description are required. Anthropic introduced the format in October 2025 and published it as an open standard that December. The portability is real, not marketing: a skill using only name, description and plain markdown runs unchanged across Claude Code, Codex, Cursor and others. Note that the skill is portable and the plugin wrapper around it is not.",
    sources: [
      {
        label: "Anthropic, Equipping agents for the real world with Agent Skills (October 2025)",
        url: "https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills",
      },
      {
        label: "The Agent Skills specification, published as an open standard (December 2025)",
        url: "https://agentskills.io",
      },
    ],
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
      "A subagent is a delegated worker running in its own context window with its own system prompt and tool allowlist, returning a summary rather than its transcript. The economics are the point: it may burn tens of thousands of tokens and hand back one or two thousand. The everyday trigger is simple — reach for one when a side task would flood the main conversation with search results, logs or file contents nobody will reference again. The isolation cuts both ways: a subagent cannot see the parent conversation, so anything it needs has to be in the delegating prompt.",
    sources: [
      {
        label: "Claude Code, Create custom subagents",
        url: "https://code.claude.com/docs/en/sub-agents",
      },
    ],
    seeAlso: ["orchestrator", "lane", "teammate"],
  },
  {
    slug: "mcp",
    term: "MCP (Model Context Protocol)",
    group: "The harness",
    band: "established",
    gloss: "Open standard for connecting agents to external systems. The window cost is real.",
    definition:
      "MCP, the Model Context Protocol, is an open standard for connecting AI applications to external systems — data, tools, prompts — implemented by Claude, ChatGPT, VS Code, Cursor and many others, so a server built once integrates everywhere. Adoption is its strongest argument, and it is now stewarded by the Agentic AI Foundation rather than by its author. The cost vendor material omits is real: most clients load every tool definition up front, so descriptions occupy the window before any work starts, and every intermediate result round-trips through the model. Install servers casually and you pay that tax on every single turn.",
    sources: [
      {
        label: "Model Context Protocol — the specification and its client list",
        url: "https://modelcontextprotocol.io",
      },
      {
        label: "Linux Foundation, formation of the Agentic AI Foundation (9 December 2025)",
        url: "https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation",
      },
    ],
    seeAlso: ["hook", "prompt-injection", "prompt-caching"],
  },
  {
    slug: "hook",
    term: "Hook",
    group: "The harness",
    band: "established",
    gloss: "A shell command the harness runs at a fixed point. Exit codes are the interface.",
    definition:
      "A hook is a shell command the harness runs at a fixed point in the agent's loop — not a request to the model. Exit codes are the interface, and the exact code matters: in Claude Code an exit of 2 blocks the transition the hook fired on and feeds the hook's stderr back to the model, while any other non-zero exit is reported and then allowed through. Writing “exit 1” in a validator and assuming it blocks is the common way to ship a gate that gates nothing. It is the only lever on this page the model cannot argue with, which is also why an untrusted repository that can write a hook has execution on your machine. The distinction worth holding: an instruction is obeyed by disposition, a hook is enforced by the harness.",
    sources: [
      {
        label: "Claude Code, Hooks reference — exit-code behaviour and blocking events",
        url: "https://code.claude.com/docs/en/hooks",
      },
    ],
    seeAlso: ["verification-gate", "worktree-isolation", "self-reported-green"],
  },
  {
    slug: "permission-level",
    term: "Permission level",
    group: "The harness",
    band: "established",
    gloss: "How much the agent may do without asking. A blast-radius control, not a correctness one.",
    definition:
      "A permission level is how much the agent may do without asking: plan-only, ask-per-action with an allowlist, auto-accept edits, or no prompts at all. It is a blast-radius control, not a verification control — raising it does not make the work more correct, only less interrupted. Anthropic's own documentation says the unrestricted mode offers no protection against prompt injection, which is the honest framing of what is being traded. This is the setting people change most often and reason about least. Pair every step up with a gate that does not depend on the model's own account of itself.",
    sources: [
      {
        label: "Claude Code, Permission modes",
        url: "https://code.claude.com/docs/en/permission-modes",
      },
    ],
    seeAlso: ["hook", "verification-gate", "worktree-isolation"],
  },
  {
    slug: "prompt-caching",
    term: "Prompt caching",
    group: "The harness",
    band: "established",
    gloss: "Reuse of a processed prefix. Makes the front of a context expensive to change.",
    definition:
      "Prompt caching is the reuse of an already-processed context prefix, billed at a fraction of fresh input — a cache hit costs a tenth of the base input rate, against a surcharge to write the entry. The prefix runs tools, then system, then messages, in that order, and the cache matches the longest one it can. So the front of a context is expensive to change and the back is cheap to extend, which is why appending to a file the agent has already read costs less than rewriting its top, and why adding one tool definition invalidates the cache for every prompt that uses tools. Most of the advice about keeping instructions stable is really an economic argument wearing a quality costume.",
    sources: [
      {
        label: "Anthropic, Prompt caching — prefix order, matching, and pricing multipliers",
        url: "https://platform.claude.com/docs/en/build-with-claude/prompt-caching",
      },
    ],
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
      "Prompt injection is the structural security problem of agentic coding: agents are compromised through the content they are designed to process. A sentence in a retrieved page, a code comment, or a tool description can redirect behaviour with no malware and no stolen credentials. Anthropic states the skills version plainly — a skill gives an agent capabilities through instructions and code, so a malicious one can direct it to invoke tools or execute code against the skill's stated purpose, up to data exfiltration. Install from sources you trust and read the bundled files. Be sceptical of the percentages: one small audit of a single signature-only MCP scanner put its false-positive rate near 78%, a much larger scan of 1,899 servers found tool poisoning in 5.5% of them, and the two numbers are measuring different things. Much of the loudest coverage comes from vendors selling the cure.",
    sources: [
      {
        label: "Anthropic, Agent Skills — security considerations",
        url: "https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview",
      },
      {
        label: "AppSec Santa, MCP Server Security Audit 2026 — the 78% false-positive finding",
        url: "https://appsecsanta.com/research/mcp-server-security-audit-2026",
      },
      {
        label: "Hasan et al., MCP at First Glance (2025) — 1,899 servers scanned, 5.5% tool poisoning",
        url: "https://arxiv.org/abs/2506.13538",
      },
    ],
    seeAlso: ["mcp", "hook", "couldnt-verify"],
  },
  {
    slug: "agentic-search",
    term: "Agentic search vs. semantic index",
    group: "The harness",
    band: "contested",
    gloss: "Grep on demand or embed the repo. Genuinely unsettled — treat certainty as a tell.",
    definition:
      "Agentic search versus semantic indexing is the live architectural disagreement in code retrieval. Claude Code does not index or embed; it greps on demand, citing precision, freshness, simplicity and privacy. Cursor indexes with tree-sitter chunking, embeddings and Merkle-tree sync, and now publishes hybrid results. Genuinely unsettled — treat anyone claiming otherwise as selling something. The framing that survives scrutiny: exact search wins when you know the string, structural navigation wins for relationships, large-context stuffing wins when the repo fits, and pure vector retrieval rarely wins on code alone.",
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
      "A task graph is work decomposed into nodes with edges recording what blocks what, so independent nodes can run concurrently and dependent ones cannot start early. The idea is not new — AutoGen's GraphFlow runs a directed graph over agents, and Anthropic documented the orchestrator-workers pattern on 19 December 2024, both well before the 2026 name for it. The useful part is the edge, not the diagram: a graph you drew but never enforced is a picture. Enforcement means native edges, and it comes with a disjointness rule most teams learn the hard way — an item blocked purely by edges must never also carry a “blocked” label, which is reserved for blockers that are not tracker items: a vendor gate, a scheduling constraint, a pending adjudication. A stale label is a phantom edge.",
    sources: [
      {
        label: "Anthropic, Building effective agents (19 December 2024) — the orchestrator-workers pattern",
        url: "https://www.anthropic.com/engineering/building-effective-agents",
      },
      {
        label: "Microsoft AutoGen, GraphFlow — a DiGraph controlling execution between agents",
        url: "https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/graph-flow.html",
      },
    ],
    seeAlso: ["frontier", "graph-engineering", "issue-as-spec"],
  },
  {
    slug: "frontier",
    term: "Frontier",
    group: "How work is arranged",
    band: "established",
    bandClaim:
      "Established as the graph-search concept the word is taken from — the nodes reachable now, separating what is explored from what is not. The tracker and interview readings below are this catalog's own application of it.",
    skill: "grilling",
    gloss: "The nodes whose prerequisites are all satisfied — the edge of what is takeable now.",
    definition:
      "A frontier is the set of nodes whose prerequisites are all satisfied — the edge of what is takeable now. The word is borrowed from graph search, where the frontier is the set of generated but not-yet-expanded nodes and its defining property is that it separates the explored part of the graph from the unexplored. On a tracker that is items which are ready-labelled, unassigned, and blocked neither by a dependency edge nor by a label. In an interview it is every decision whose prerequisites are already settled. Same word, same meaning, two surfaces. An empty frontier is a fact that needs a reason attached — all claimed, triage stalled, or everything blocked — because an empty answer with no breakdown sends people guessing.",
    sources: [
      {
        label:
          "Russell & Norvig, Artificial Intelligence: A Modern Approach, 3rd ed. — ch. 3, “Solving Problems by Searching” (publisher's sample chapter)",
        url: "https://www.pearsonhighered.com/assets/samplechapter/0/1/3/6/0136042597.pdf",
      },
    ],
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
      "Fog is work whose open questions gate each other, so nobody can spec it in one sitting. Fog density picks the instrument: deep fog gets a ticket per question, resolved most-gating-first; shallow fog gets a single sitting. The move most teams skip is the no-fog exit — when the survey finds every question answerable from what already exists, stop and write an ordinary spec. A map with nothing undecided is overhead, not planning.",
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
      "A tracer bullet is a thin slice that goes all the way through the system rather than a horizontal layer that goes nowhere alone. It is Hunt and Thomas's term, and explicitly not a prototype — in their words, prototyping generates disposable code, while tracer code is lean but complete and forms part of the skeleton of the final system. Three tests, this catalog's rather than theirs: verifiable alone, PR-sized, ordered by what it unblocks. “Build the data layer” fails all three, because its acceptance criteria are always someone else's.",
    sources: [
      {
        label: "Hunt & Thomas, The Pragmatic Programmer — Tracer Bullets",
        url: "https://pragprog.com/titles/tpp20/the-pragmatic-programmer-20th-anniversary-edition/",
      },
    ],
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
      "Issue-as-spec is the practice of making the work item's body the spec — destination, acceptance criteria, out of scope — written once on the tracker before any code. The implementing brief adds standing constraints and mechanics, never a second copy of the requirements, and the work summary posts back to the item so the tracker stays the durable record. The readiness bar is a handoff test: an item is ready only when its body could be handed to a stranger.",
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
      "A lane is a working session — agent or human — in its own workspace on its own branch, holding exactly one work item. Lanes commit on their branch and stop; integration belongs to whoever routed them. The vocabulary is not standardised: other systems say teammate, worker, or agent. What is standard is the constraint underneath it — two workers editing one file leads to overwrites, so the work has to be broken up until each owns a different set of files.",
    seeAlso: ["orchestrator", "teammate", "claim", "worktree-isolation"],
  },
  {
    slug: "teammate",
    term: "Teammate (agent teams)",
    group: "How work is arranged",
    band: "emerging",
    gloss: "The vendor word for a lane, with the mechanics shipped. Guidance is three to five.",
    definition:
      "A teammate is the vendor's name for what this catalog calls a lane, with the coordination mechanics shipped rather than improvised: pending tasks whose dependencies are unresolved cannot be claimed, claims lock files, and each teammate has a mailbox. The documentation's own guidance is three to five, and it names dependency-heavy or same-file work as the wrong fit — which is the same constraint the lane entry states, arrived at independently.",
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
      "A claim is a record of ownership of a work item, written before anyone touches it, in a form a machine can read. An assignee field alone cannot distinguish two sessions sharing one account, so the claim is a comment marker a scanner can match. Taking over requires evidence that the previous lane is dead, and death is hard to prove: an agent session can be alive but between turns, invisible to every process probe. No processes and no commits is not evidence.",
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
      "An orchestrator is one session that routes work into lanes, audits what comes back, owns integration, and never implements. The rules that make it work are the non-obvious ones: exactly one live orchestrator at a time, because two of them routing the same board is the same collision class as two sessions building the same item; delegation moves the executor and never the standard; and context is the orchestrator's scarcest resource, which makes delegation a context-preservation technique before it is a throughput one.",
    seeAlso: ["lane", "subagent", "self-reported-green", "the-decider"],
  },
  {
    slug: "worktree-isolation",
    term: "Worktree isolation",
    group: "How work is arranged",
    band: "established",
    gloss: "Separate directories over one object store. Not a security boundary.",
    definition:
      "Worktree isolation is giving each parallel agent its own checked-out directory over one shared object store. It works for what it claims — separate files, separate branches, no lock contention — and it is not a security boundary, which is the half nobody repeats. Git's own repository-layout documentation is explicit about the shared half: objects, hooks, config, packed-refs and every ref outside bisect, rewritten and worktree all resolve to the common directory instead of the worktree's own. So an agent inside a worktree can install a pre-commit hook that runs as you on your next commit. The usual objection to cloning instead — that it is slow — does not hold at the repository sizes anyone here works at. Worktree when a person drives; clone when something else does.",
    sources: [
      {
        label: "Git, gitrepository-layout — which paths resolve to $GIT_COMMON_DIR",
        url: "https://git-scm.com/docs/gitrepository-layout",
      },
      {
        label: "Git, git-worktree — shared refs and the shared config file",
        url: "https://git-scm.com/docs/git-worktree",
      },
    ],
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
      "A handoff artifact is one small file capturing where the work stands, so a fresh session resumes with no re-explanation. It is written at roughly half the window rather than when it fills, because the oldest details fall away and long-chain reasoning degrades before the hard limit is ever reached. Two rules keep it useful: overwrite rather than append, since an appended handoff decays into a transcript nobody reads; and stay a pointer rather than a transcript, linking the durable records instead of copying them.",
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
      "The stale-NEXT rule is that a handoff points at the tracker query and never enumerates work items. A listed item number goes stale the moment another session claims it, and a session starting from that list collides with the claimer. The corollary is the part people skip: reading a handoff never authorises starting an item — the claim runs first. It is the clearest example on this page of why you defer to a live graph instead of snapshotting one.",
    seeAlso: ["handoff-artifact", "claim", "frontier"],
  },

  // ── Verification and authority ─────────────────────────────────────────────
  {
    slug: "verification-gate",
    term: "Verification gate",
    group: "Verification and authority",
    band: "established",
    bandClaim:
      "Established as a mechanism: harness-enforced gates are documented and in wide use. The phrase itself is inherited from process engineering's quality gate and has no single coiner.",
    skill: "orchestrate",
    gloss: "A check the model cannot argue past, because the harness enforces it.",
    definition:
      "A verification gate is a check the model cannot argue its way past, because the harness enforces it rather than the model. A hook that blocks a transition on the harness's blocking exit code is one shape; pre-commit hooks and required CI status checks on a protected branch are the same shape. Prefer deterministic graders where you can get them: a validator can prove a field is missing, where a model can only argue that its work is complete.",
    sources: [
      {
        label: "Claude Code, Hooks reference — which events a hook can block",
        url: "https://code.claude.com/docs/en/hooks",
      },
      {
        label: "GitHub, protected branches and required status checks",
        url: "https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches",
      },
    ],
    seeAlso: ["hook", "oracle", "self-reported-green", "llm-as-judge"],
  },
  {
    slug: "oracle",
    term: "Oracle",
    group: "Verification and authority",
    band: "established",
    bandClaim:
      "Established as a concept: software testing has studied the oracle problem for decades. The closing claim about agent performance is this catalog's own observation and is marked as such.",
    gloss: "An independent source of truth about correctness. Where none exists, gates degrade.",
    definition:
      "An oracle is an independent source of truth that can say whether an output is correct without a human reading it: a reference implementation, a differential comparison against a known-good tool, a property test, a type checker. Software testing has called the difficulty of obtaining one the oracle problem since long before agents existed, and the surveyed answers — specifications, contracts, metamorphic testing — all end at a human where none of them fit. Where an oracle exists, verification is cheap and parallelism is safe. Where none exists, every gate on this page degrades into a model arguing that it is finished. On this catalog's evidence, whether a task has an oracle predicts more about how well agents do on it than any topology or prompt does — an operator's observation from running the work, not a measured result, and offered as one.",
    sources: [
      {
        label: "Barr, Harman, McMinn, Shahbaz & Yoo, The Oracle Problem in Software Testing: A Survey (IEEE TSE, 2015)",
        url: "https://doi.org/10.1109/TSE.2014.2372785",
      },
    ],
    seeAlso: ["verification-gate", "llm-as-judge", "agentic-engineering", "self-reported-green"],
  },
  {
    slug: "self-reported-green",
    term: "Self-reported green",
    group: "Verification and authority",
    band: "established",
    bandClaim:
      "Established as the shell behaviour it warns about — a pipeline reports its last command's status unless pipefail is set. The phrase itself is this catalog's own.",
    skill: "orchestrate",
    gloss: "A claim that verification passed, offered instead of evidence. Re-run it.",
    definition:
      "Self-reported green is an agent's claim that verification passed, offered in place of evidence. Re-run it. Require per-command exit codes with zero skipped checks, and remember that piped output is not evidence: the bash manual is explicit that a pipeline's exit status is the status of its last command unless “pipefail” is set, so a test command piped into “tail” reads green whenever “tail” does. This is a bug most teams have shipped at least once, usually in CI, usually for months.",
    sources: [
      {
        label: "GNU Bash Reference Manual, Pipelines — pipeline exit status and pipefail",
        url: "https://www.gnu.org/software/bash/manual/html_node/Pipelines.html",
      },
    ],
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
      "LLM-as-judge is the use of a model to grade another model's output against a rubric, either as an evaluation or as an inline gate. It is now standard and economically viable, with limitations severe enough that any honest description leads with them. Position, verbosity and self-enhancement bias were catalogued in the paper that named the technique. On code specifically, swapping which of two candidates is shown first has been measured to move judging accuracy by more than ten points. And position bias is strongest exactly where a judge is most needed: it scales with how close the candidates are in quality. Scores also run systematically optimistic. Treat judges as signal and deterministic checks as gates.",
    sources: [
      {
        label: "Zheng et al., Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena (NeurIPS 2023)",
        url: "https://arxiv.org/abs/2306.05685",
      },
      {
        label: "Jiang et al., CodeJudgeBench (2025) — order swaps moving code-judging accuracy by more than ten points",
        url: "https://arxiv.org/abs/2507.10535",
      },
      {
        label: "Shi et al., Judging the Judges (2024) — position bias scales with the quality gap",
        url: "https://arxiv.org/abs/2406.07791",
      },
    ],
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
      "Adversarial review is running several reviewers with deliberately different lenses, or several investigators told to disprove each other, rather than one reviewer working sequentially. The rationale is anchoring: once one theory is explored, later investigation bends toward it, and a single reviewer gravitates to one class of issue at a time. The mechanism is sound and cheap to try. The supporting evidence is vendor-stated rather than benchmarked, and nobody should pretend otherwise.",
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
      "Echo risk is the possibility that agreement between models is not evidence at all. Convergence is earned when reviewers reached the same answer independently, and social when they read each other and drifted into agreement. The distinction is measurable in a crude way — verdict flips toward the majority, overlapping citation sets, self-reported deference — and worth measuring, but the honest claim is narrow: it flags possible echo, it does not prove independence. High overlap can be an honest read of a small source.",
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
      "Couldn't-verify is an explicit bucket for claims a review leaned on but did not check, plus the blind spots no reviewer could see. It is the main guard against a confident, unanimous, wrong answer, because several models can converge on the same missing fact. Its sharper cousin: a verified citation means the receipt resolves — the cited line exists and the quoted text is there — not that the inference drawn from it is sound. The gate catches fabrication, not grounded-but-wrong reasoning.",
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
      "The decider is the named person who adjudicates decisions in a repo: always asked, never inferred. It is the one role every skill in this catalog defers to, and binding it to an actual name is the first thing setup does. The failure it prevents is specific and common — an agent that answers its own questions has produced nothing but a transcript of itself.",
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
      "Graph engineering is, as the phrase has been used since July 2026, a name for task-graph orchestration: decompose a goal into a dependency graph, run independent nodes concurrently, gate integration behind completed prerequisites. A separate community uses the same words for code knowledge graphs, and the two have nothing to do with each other. The patterns are real, and Anthropic documented them on 19 December 2024 without ever using the word “graph”; no comparative benchmark for the labelled version exists. The advocacy literature concedes it outright: “Calling the practice graph engineering is a naming event, not a technical one.”",
    seeAlso: ["task-graph", "loop-engineering", "code-knowledge-graph", "orchestrator"],
  },
  {
    slug: "loop-engineering",
    term: "Loop engineering",
    group: "Unsurveyed water",
    band: "emerging",
    gloss: "Designing the system that prompts the agent, instead of prompting it yourself.",
    definition:
      "Loop engineering is designing the system that prompts the agent instead of prompting it yourself. Addy Osmani named it on 7 June 2026, and is explicit that he did not invent the practice — he credits Peter Steinberger's formulation and Boris Cherny's account of running loops rather than prompting. The practice is real and the load-bearing part is the caveats, which the marketing versions drop: a loop running unattended is a loop making mistakes unattended, and “done” is a claim rather than proof.",
    sources: [
      {
        label: "Addy Osmani, Loop Engineering: designing loops that prompt coding agents (7 June 2026)",
        url: "https://addyosmani.com/blog/loop-engineering/",
      },
    ],
    seeAlso: ["graph-engineering", "verification-gate", "oracle"],
  },
  {
    slug: "agentic-engineering",
    term: "Agentic engineering",
    group: "Unsurveyed water",
    band: "emerging",
    gloss: "Directing fallible agents under human oversight. Automates what you can verify.",
    definition:
      "Agentic engineering is Andrej Karpathy's successor framing to vibe coding — the term he coined in February 2025 for accepting generated code without reading it, and later bounded rather than disowned: “Vibe coding raises the floor. Agentic engineering is about extrapolating the ceiling.” The framing is directing fallible agents under structured human oversight rather than writing the code yourself, with people in charge of the spec and the plan. The most load-bearing line is about scope: traditional computers automate what you can specify in code, and this round of models automates what you can verify — which is why capability peaks in verifiable domains.",
    sources: [
      {
        label: "Andrej Karpathy, Sequoia AI Ascent 2026 — his own summary, carrying the floor/ceiling line",
        url: "https://karpathy.bearblog.dev/sequoia-ascent-2026/",
      },
    ],
    seeAlso: ["oracle", "the-decider", "verification-gate"],
  },
  {
    slug: "code-knowledge-graph",
    term: "Code knowledge graph",
    group: "Unsurveyed water",
    band: "emerging",
    gloss: "Index the repo as symbols and relationships. Building it is the easy half.",
    definition:
      "A code knowledge graph is an index of a repository as symbols and relationships — call edges, imports, inheritance, tests — so an agent traverses dependencies rather than matching strings. This half has the actual evidence: RepoGraph, CodexGraph and LocAgent all report retrieval or localisation gains, and CodeCompass ran a controlled three-arm comparison against a plain agent and against BM25 retrieval. The finding that matters most for anyone building one is behavioural, not technical: across CodeCompass's 258 trials, 58% of the runs that had graph access made zero tool calls, and agents needed explicit prompting before they would use it at all. Building the index is the easy half.",
    sources: [
      {
        label: "CodeCompass: Navigating the Navigation Paradox in Agentic Code Intelligence (2026) — the three-arm comparison and the 58% figure",
        url: "https://arxiv.org/abs/2602.20048",
      },
      {
        label: "Ouyang et al., RepoGraph: repository-level code graphs for AI software engineering",
        url: "https://arxiv.org/abs/2410.14684",
      },
      {
        label: "Liu et al., CodexGraph: bridging LLMs and code repositories via graph databases",
        url: "https://arxiv.org/abs/2408.03910",
      },
      {
        label: "LocAgent: graph-guided LLM agents for code localisation — the LocBench results",
        url: "https://arxiv.org/abs/2503.09089",
      },
    ],
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
      "Spec-driven development is writing a spec first and generating from it, rather than prompting straight to code. GitHub's spec-kit ships a real pipeline — constitution, specify, plan, tasks, implement — with a clarify step for underspecified areas and a checklist step honestly described as “unit tests for English.” Real tooling with real adoption. Be sceptical of the stronger claim that specs are literally executable, which overstates what a markdown file does; this catalog's version puts the spec in the work item instead.",
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
 * Every see-also must resolve, every skill named must be in the catalog, every
 * entry must open by naming its term, and every `established` entry must cite
 * the primary source its band claims exists.
 *
 * Called from the page so a broken cross-link or an uncited "established" fails
 * `next build` rather than shipping — the legend's whole value is that its links
 * go somewhere and its bands mean something.
 */
/**
 * The part of a term a definition has to say out loud. Parentheticals and the
 * alternative half of a slashed or "vs." heading are dropped, so "Agent Skill
 * (SKILL.md)" only obliges the entry to say "Agent Skill".
 */
function termHead(term: string): string {
  return term
    .replace(/\s*\([^)]*\)/g, "")
    .split(/\s+\/\s+| vs\.? /)[0]
    .trim();
}

export function assertLegendSound(skillSlugs: string[]): void {
  const slugs = new Set(ENTRIES.map((e) => e.slug));
  const known = new Set(skillSlugs);
  const problems: string[] = [];

  for (const entry of ENTRIES) {
    // Rule 5, enforced rather than merely written down: the first sentence is
    // what a reader skims and what an answer engine quotes, so it has to name
    // the thing being defined.
    const opening = entry.definition.split(/\.\s/)[0];
    const head = termHead(entry.term);
    if (!opening.toLowerCase().includes(head.toLowerCase())) {
      problems.push(
        `${entry.slug}: opening sentence never says "${head}". Definitions open by naming the term.`,
      );
    }
    if (/<[a-z/][^>]*>/i.test(entry.definition)) {
      // Definitions render as a React text child and as plain markdown, so a
      // tag here reaches the reader as literal angle brackets.
      problems.push(`${entry.slug}: definition contains markup. Definitions are plain text.`);
    }
    for (const ref of entry.seeAlso ?? []) {
      if (!slugs.has(ref)) problems.push(`${entry.slug}: see-also "${ref}" does not exist`);
    }
    if (entry.skill && !known.has(entry.skill)) {
      problems.push(`${entry.slug}: names skill "${entry.skill}", which is not in the catalog`);
    }
    if (!GROUPS.some((g) => g.name === entry.group)) {
      problems.push(`${entry.slug}: group "${entry.group}" is not declared`);
    }
    if (entry.band === "established" && !entry.sources?.length) {
      problems.push(
        `${entry.slug}: banded "established" but cites no source. Add one, or re-band it.`,
      );
    }
    for (const source of entry.sources ?? []) {
      if (!source.url.startsWith("https://")) {
        problems.push(`${entry.slug}: source "${source.label}" is not an https URL`);
      }
    }
  }

  if (problems.length) throw new Error(`legend.ts:\n  ${problems.join("\n  ")}`);
}
