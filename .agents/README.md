# agent-team Agents & Skills

Workspace subagents are located in `.agents/agents/{agent_name}/agent.md`.

Both **Codex**, **Claude Code**, and **Antigravity CLI (`agy`)** discover the agents in this workspace:
- **agy** reads `.agents/agents/{agent_name}/agent.md`, `.agents/agents.json`, and `.agents/skills.json`.
- **Codex** reads `.agents/agents/{agent_name}/agent.toml` registered via `../.codex/config.toml`.
- **Claude Code** reads `.claude/agents/{agent_name}.md` and `CLAUDE.md`.

## Agent Roles & Model Mapping

| Role | Workspace Path | Model (Agy) | Model (Codex) | Fallback Chain | Purpose |
| --- | --- | --- | --- | --- | --- |
| `lead-architect` | `.agents/agents/lead-architect/agent.md` | `gemini-4-argon-high` | `gpt-6-astra` (high) | `agy:gemini-4-argon-high → agy:claude-opus-5-5-medium → agy:gemini-3.8-flash-high → codex:gpt-6-astra (high)` | Lead Solution Architect & Planner — Formulate initial architecture proposals, technical design blueprints, module contracts, and task breakdowns. Defend and refine the plan across 2 structured debate rounds with lead-critic until consensus is reached, then hand off the approved blueprint to the orchestrator for execution. |
| `lead-critic` | `.agents/agents/lead-critic/agent.md` | `gemini-3.1-pro-high` | `gpt-6.1-sol` (xhigh) | `agy:gemini-3.1-pro-high → agy:claude-opus-5-5-medium → agy:gemini-3.8-flash-high → codex:gpt-6.1-sol (xhigh)` | Lead Technical Critic & Challenger — Stress-test architecture and design proposals in a bounded 2-round debate with lead-architect. Identify hidden assumptions, concurrency/security risks, scalability bottlenecks, and YAGNI/over-engineering. Issue final sign-off (CONSENSUS_REACHED) only when all critical concerns are resolved. |
| `orchestrator` | `.agents/agents/orchestrator/agent.md` | `gemini-4-argon-high` | `gpt-6-astra` (high) | `agy:gemini-4-argon-high → agy:claude-opus-5-5-medium → agy:gemini-3.8-flash-high → codex:gpt-6.1-sol (xhigh)` | Lead Execution Orchestrator — Receive the finalized architecture blueprint approved from the 2-round lead debate (lead-architect ⮂ lead-critic). Coordinate execution by dispatching searcher for codebase scouting, implementer for TDD coding, reviewer for independent code review, and committer for Conventional Commits. Verify overall integration without modifying production code directly. |
| `reviewer` | `.agents/agents/reviewer/agent.md` | `gemini-3.1-pro-high` | `gpt-6.1-sol` (xhigh) | `agy:gemini-3.1-pro-high → agy:claude-opus-5-5-medium → agy:gemini-3.8-flash-high → codex:gpt-6.1-sol (xhigh)` | Independent Code Quality & Security Reviewer — Independently review changes in read-only mode: detect logic bugs, async race conditions, security vulnerabilities, unvalidated inputs, and missing regression tests. Report actionable defects with exact file/line, impact, and smallest safe fix. |
| `designer` | `.agents/agents/designer/agent.md` | `gemini-3.8-flash-high` | `gpt-6-sol` (xhigh) | `agy:gemini-3.8-flash-high → agy:gemini-3.1-pro-high → claude:sonnet → codex:gpt-6-sol (xhigh)` | UI/UX & Anti-Slop Visual Designer — Design and implement pixel-perfect, anti-slop frontend interfaces, UI components, animations, and visual assets adhering to strict design taste and design systems. |
| `implementer` | `.agents/agents/implementer/agent.md` | `gemini-3.8-flash-high` | `gpt-6-sol` (xhigh) | `agy:gemini-3.8-flash-high → agy:gemini-3.1-pro-high → claude:sonnet → codex:gpt-6-sol (xhigh)` | Senior Feature & TDD Implementer — Implement and test with the smallest complete changes: write regression/unit tests first, run them to verify failure (Red), implement the minimal code to pass (Green), and refactor. |
| `searcher` | `.agents/agents/searcher/agent.md` | `gemini-3.8-flash-medium` | `gpt-6-luna` (medium) | `agy:gemini-3.8-flash-medium → agy:gemini-3.8-flash-high → claude:haiku → codex:gpt-6-luna (medium)` | Primary Documentation & Codebase Scout — Research focused questions against primary documentation and scout the codebase in read-only mode. Return concise findings with direct URLs, API signatures, exact file:line paths, and compatibility limits. |
| `committer` | `.agents/agents/committer/agent.md` | `gemini-3.7-flash` | `gpt-6-luna` (low) | `agy:gemini-3.7-flash → agy:gemini-3.8-flash-medium → claude:haiku → codex:gpt-6-luna (low)` | Conventional Git Committer — Inspect git status (`git status -s`, `git diff --staged`) and craft concise, professional commit messages in Conventional Commits format (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`). |

## Project Context & Goal

- **Context**: Dự án agent-team (Python). Giữ thay đổi nhỏ gọn, ưu tiên TDD và kiểm định độc lập.
- **Goal**: Develop, test, and maintain agent-team with 2-phase lead debate & execution team.

## Applied Skills

- **`agy-customizations`**: Comprehensive guide and reference for the Antigravity Customization System.
- **`antigravity-guide`**: Provides a comprehensive guide, quick reference, and sitemap for Google Antigravity (AGY), including the Antigravity CLI (agy), Antigravity 2.0, Antigravity IDE, Python SDK, slash commands, keybindings, and customizations (skills, rules, MCP, sidecars). Activate this skill when the user asks questions about how to use, configure, or customize Antigravity, AGY, the agy CLI, the Antigravity IDE, or Antigravity 2.0.
- **`brainstorming`**: You MUST use this before any creative work - creating features, building components, adding functionality, modifying behavior, or planning anything new, in software or out of it (a talk, a business, a renovation).
- **`code-review`**: Review the changes since a fixed point (commit, branch, tag, or merge-base) along two axes: Standards (does the code follow this repo's documented coding standards?) and Spec (does the code match what the originating issue/spec asked for?). Runs both reviews in parallel sub-agents and reports them side by side. Use when the user wants to review a branch, a PR, work-in-progress changes, or asks to \"review since X\".
- **`codebase-design`**: Shared vocabulary for designing deep modules. Use when the user wants to design or improve a module's interface, find deepening opportunities, decide where a seam goes, make code more testable or AI-navigable, or when another skill needs the deep-module vocabulary.
- **`diagnosing-bugs`**: Diagnosis loop for hard bugs and performance regressions. Use when the user says "diagnose"/"debug this", or reports something broken/throwing/failing/slow.
- **`dispatching-parallel-agents`**: Use when facing 2+ independent tasks that can be worked on without shared state or sequential dependencies
- **`domain-modeling`**: Build and sharpen a project's domain model. Use when discussing codebase terminology, writing or editing a GLOSSARY.md, or recording or editing an ADR.
- **`executing-plans`**: Use when executing an implementation plan in the current session as the implementer yourself — your human partner chose inline execution, or no subagent tool is available
- **`finishing-a-development-branch`**: Use when implementation is complete, all tests pass, and you need to decide how to integrate the work
- **`grilling`**: Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases.
- **`ponytail`**: Lazy senior dev mode: the smallest change that fully solves the task, and a
- **`ponytail-audit`**: Quality audit of a whole repo: bugs, security holes, what breaks under real
- **`ponytail-debt`**: List every `shortcut:` comment (and older `ponytail:` ones) as a debt ledger. One-shot report,
- **`ponytail-help`**: Quick reference for ponytail levels, skills and commands. One-shot display.
- **`ponytail-review`**: Quality review of a change: is the logic right, is it safe, does it hold
- **`pr`**: Use when writing a PR body.
- **`receiving-code-review`**: Use when receiving code review feedback, before implementing suggestions, especially if feedback seems unclear or technically questionable - requires technical rigor and verification, not performative agreement or blind implementation
- **`requesting-code-review`**: Use when completing tasks, implementing major features, or before merging to verify work meets requirements
- **`research`**: Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent.
- **`subagent-driven-development`**: Use when executing implementation plans with independent tasks in the current session
- **`swarm`**: Run a swarm: several agents working in parallel on one task, each in its own
- **`systematic-debugging`**: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
- **`tdd`**: Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions "red-green-refactor", or wants integration tests.
- **`test-driven-development`**: Use when implementing any feature or bugfix, before writing implementation code
- **`verification-before-completion`**: Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always
- **`writing-for-agents`**: Writing documents for agents. Use when creating or editing skills, or modifying AGENTS.md or CLAUDE.md.
- **`writing-plans`**: Use when you have a spec or requirements for a multi-step task, before touching code
