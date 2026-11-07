# agent-team Agents & Skills

Workspace subagents are located in `.agents/agents/{agent_name}/agent.md`.

Both **Codex**, **Claude Code**, and **Antigravity CLI (`agy`)** discover the agents in this workspace natively:
- **agy** reads `.agents/agents/{agent_name}/agent.md`, `.agents/agents.json`, and `.agents/skills.json`.
- **Codex** reads `.agents/agents/{agent_name}/agent.toml` registered via `.codex/config.toml`.
- **Claude Code** reads `.claude/agents/{agent_name}.md` and `CLAUDE.md`.

## Agent Roles & Model Mapping

| Role | Workspace Path | Model (Agy) | Model (Codex) | Fallback Chain | Purpose |
| --- | --- | --- | --- | --- | --- |
| `lead-architect` | `.agents/agents/lead-architect/agent.md` | `gemini-4-argon-high` | `gpt-6-astra` (high) | `agy:gemini-4-argon-high → agy:claude-opus-5-5-medium → agy:gemini-3.8-flash-high → codex:gpt-6-astra (high)` | Lead Solution Architect & Planner — Xây dựng đề xuất kiến trúc sơ bộ, thông số kỹ thuật (RFC), hợp đồng module và kế hoạch phân rã nhiệm vụ. Bảo vệ và tinh chỉnh giải pháp qua 2 vòng phản biện kỹ thuật chặt chẽ với lead-critic đến khi đạt đồng thuận, sau đó bàn giao bản thiết kế hoàn thiện cho orchestrator điều phối thực thi. |
| `lead-critic` | `.agents/agents/lead-critic/agent.md` | `gemini-3.1-pro-high` | `gpt-6.1-sol` (xhigh) | `agy:gemini-3.1-pro-high → agy:claude-opus-5-5-medium → agy:gemini-3.8-flash-high → codex:gpt-6.1-sol (xhigh)` | Lead Technical Critic & Challenger — Kiểm thử áp lực (stress-test) các đề xuất kiến trúc và kế hoạch phân rã từ lead-architect qua 2 vòng phản biện. Vạch rõ điểm mù, rủi ro bảo mật, nghẽn hiệu năng, và loại bỏ sự phức tạp hóa thừa thãi (YAGNI/Over-engineering). Chỉ phê duyệt và cấp chứng nhận đồng thuận (CONSENSUS_REACHED) khi kế hoạch đạt độ tin cậy và an toàn cao. |
| `orchestrator` | `.agents/agents/orchestrator/agent.md` | `gemini-4-argon-high` | `gpt-6-astra` (high) | `agy:gemini-4-argon-high → agy:claude-opus-5-5-medium → agy:gemini-3.8-flash-high → codex:gpt-6.1-sol (xhigh)` | Lead Execution Orchestrator — Tiếp nhận bản thiết kế kiến trúc hoàn thiện đã đạt đồng thuận từ cặp Lead phản biện (lead-architect ⮂ lead-critic). Điều phối thực thi phân cấp: cho phép fan-out các tác vụ đọc độc lập (searcher); giữ các tác vụ sửa file chung (implementer, designer), kiểm định độc lập (reviewer) và commit (committer) theo đúng thứ tự tuần tự. Giữ vai trò kiểm chứng tích hợp, không tự sửa code sản phẩm trực tiếp. |
| `reviewer` | `.agents/agents/reviewer/agent.md` | `gemini-3.1-pro-high` | `gpt-6.1-sol` (xhigh) | `agy:gemini-3.1-pro-high → agy:claude-opus-5-5-medium → agy:gemini-3.8-flash-high → codex:gpt-6.1-sol (xhigh)` | Independent Code Quality & Security Reviewer — Kiểm định độc lập các thay đổi ở chế độ chỉ đọc: phát hiện lỗi logic, xung đột bất đồng bộ, lỗ hổng bảo mật, đầu vào chưa kiểm tra và thiếu bài test hồi quy. Báo cáo rõ file:dòng, mức độ ảnh hưởng và hướng sửa nhỏ gọn, an toàn nhất. |
| `designer` | `.agents/agents/designer/agent.md` | `gemini-3.8-flash-high` | `gpt-6-sol` (high) | `agy:gemini-3.8-flash-high → agy:gemini-3.1-pro-high → claude:sonnet → codex:gpt-6-sol (xhigh)` | UI/UX & Anti-Slop Visual Designer — Thiết kế và triển khai giao diện frontend chuẩn mực, loại bỏ slop, đảm bảo tính thẩm mỹ pixel-perfect, design system và trải nghiệm người dùng cao cấp. |
| `implementer` | `.agents/agents/implementer/agent.md` | `gemini-3.8-flash-high` | `gpt-6-sol` (xhigh) | `agy:gemini-3.8-flash-high → agy:gemini-3.1-pro-high → claude:sonnet → codex:gpt-6-sol (xhigh)` | Senior Feature & TDD Implementer — Thực thi và kiểm thử với thay đổi nhỏ gọn, trọn vẹn nhất: viết bài test đơn vị/hồi quy trước, chạy xác nhận fail (Red), viết code tối thiểu để vượt qua bài test (Green) và làm sạch code. |
| `searcher` | `.agents/agents/searcher/agent.md` | `gemini-3.8-flash-medium` | `gpt-6-luna` (medium) | `agy:gemini-3.8-flash-medium → agy:gemini-3.8-flash-high → claude:haiku → codex:gpt-6-luna (medium)` | Primary Documentation & Codebase Scout — Tra cứu các câu hỏi trọng tâm trên tài liệu chính thống và khảo sát codebase ở chế độ chỉ đọc. Trả về báo cáo cô đọng kèm URL, chữ ký API, đường dẫn file:dòng và các giới hạn tương thích. |
| `committer` | `.agents/agents/committer/agent.md` | `gemini-3.7-flash` | `gpt-6-luna` (low) | `agy:gemini-3.7-flash → agy:gemini-3.8-flash-medium → claude:haiku → codex:gpt-6-luna (low)` | Conventional Git Committer — Kiểm tra trạng thái git (`git status -s`, `git diff --staged`) và soạn thông điệp commit ngắn gọn, chuẩn Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`). |

## Host-Native Orchestration (Zero Custom Runtime)

`agent-team` (`agt`) operates strictly as a multi-harness scaffold and generator. It avoids adding custom runtime daemons or process emulators to simulate agents:
- **Antigravity (`agy`)**: Orchestration is driven via host-native `invoke_subagent` and `send_message` tools using definitions in `.agents/agents/`.
- **OpenAI Codex (`codex`)**: Uses native multi-agent thread dispatch enabled via `[agents]` configurations in `.codex/config.toml`.
- **Claude Code (`claude`)**: Orchestrates via subagent markdown profiles in `.claude/agents/` referenced through `CLAUDE.md`.

## Execution Concurrency & Ordering Contract

To balance execution throughput and correctness, all dispatches must follow these ordering principles:
1. **Parallel Read Fan-Out**: Independent codebase scouting and documentation search tasks (`searcher`) can fan out in parallel to maximize discovery speed.
2. **Ordered Shared-File Edits (Single-Writer)**: Implementation tasks (`implementer`, `designer`) that touch overlapping files or shared module contracts must execute sequentially with strict single-writer boundaries.
3. **Ordered Verification & Commit**: Once implementation passes local unit tests, `reviewer` performs an independent 2-axis quality and security review. Only after `reviewer` grants `APPROVED`, `committer` packages atomic Conventional Commits.

## Workflow Graph Decision Boundary

A graph-based state machine or formal workflow orchestrator is NOT required for standard linear development. Consider introducing an external workflow graph only when the target environment demands:
- **Gate Enforcement**: Enforcing programmatic host quality gates that strictly prevent progression before formal sign-off.
- **State Checkpointing & Resumption**: Checkpointing execution state to disk so long-running multi-step operations can pause, survive host restarts, and resume gracefully.
- **Systematic Retry Loops**: Managing automated remediation cycles where failed review or verification steps automatically re-dispatch targeted worker prompts.

Do not introduce a custom runtime or graph engine merely to represent role hierarchy.

## Project Context & Goal

- **Context**: Dự án agent-team (Python). Giữ thay đổi nhỏ gọn, ưu tiên TDD và kiểm định độc lập.
- **Goal**: Develop, test, and maintain agent-team with 2-phase lead debate & execution team.

## Applied Skills

- **`agy-customizations`**: Comprehensive guide and reference for the Antigravity Customization System.
- **`antigravity-guide`**: Provides a comprehensive guide, quick reference, and sitemap for Google Antigravity (AGY), including the Antigravity CLI (agy), Antigravity 2.0, Antigravity IDE, Python SDK, slash commands, keybindings, and customizations (skills, rules, MCP, sidecars). Activate this skill when the user asks questions about how to use, configure, or customize Antigravity, AGY, the agy CLI, the Antigravity IDE, or Antigravity 2.0.
- **`banner-design`**: Design banners for social media, ads, website heroes, creative assets, and print. Multiple art direction options with optional generated or supplied visuals. Actions: design, create, generate banner. Platforms: Facebook, Twitter/X, LinkedIn, YouTube, Instagram, Google Display, website hero, print. Styles: minimalist, gradient, bold typography, photo-based, illustrated, geometric, retro, glassmorphism, 3D, neon, duotone, editorial, collage.
- **`brainstorming`**: You MUST use this before any creative work - creating features, building components, adding functionality, modifying behavior, or planning anything new, in software or out of it (a talk, a business, a renovation).
- **`brand`**: Brand voice, visual identity, messaging frameworks, asset management, brand consistency. Activate for branded content, tone of voice, marketing assets, brand compliance, style guides.
- **`code-review`**: Review the changes since a fixed point (commit, branch, tag, or merge-base) along two axes: Standards (does the code follow this repo's documented coding standards?) and Spec (does the code match what the originating issue/spec asked for?). Runs both reviews in parallel sub-agents and reports them side by side. Use when the user wants to review a branch, a PR, work-in-progress changes, or asks to \"review since X\".
- **`codebase-design`**: Shared vocabulary for designing deep modules. Use when the user wants to design or improve a module's interface, find deepening opportunities, decide where a seam goes, make code more testable or AI-navigable, or when another skill needs the deep-module vocabulary.
- **`design`**: Comprehensive design skill: brand identity, design tokens, UI styling, logo generation (55 styles, Gemini, Atlas Cloud, or MuAPI AI), corporate identity program (50 deliverables, CIP mockups), HTML presentations (Chart.js), banner design (22 styles, social/ads/web/print), icon design (15 styles, SVG, Gemini 3.1 Pro), social photos (HTML→screenshot, multi-platform). Actions: design logo, create CIP, generate mockups, build slides, design banner, generate icon, create social photos, social media images, brand identity, design system. Platforms: Facebook, Twitter, LinkedIn, YouTube, Instagram, Pinterest, TikTok, Threads, Google Ads.
- **`design-system`**: Token architecture, component specifications, and slide generation. Three-layer tokens (primitive→semantic→component), CSS variables, spacing/typography scales, component specs, strategic slide creation. Use for design tokens, systematic design, brand-compliant presentations.
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
- **`slides`**: Create strategic HTML presentations with Chart.js, design tokens, responsive layouts, copywriting formulas, and contextual slide strategies.
- **`subagent-driven-development`**: Use when executing implementation plans with independent tasks in the current session
- **`swarm`**: Run a swarm: several agents working in parallel on one task, each in its own
- **`systematic-debugging`**: Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes
- **`tdd`**: Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions "red-green-refactor", or wants integration tests.
- **`test-driven-development`**: Use when implementing any feature or bugfix, before writing implementation code
- **`ui-styling`**: Create beautiful, accessible user interfaces with shadcn/ui components (built on Radix UI + Tailwind), Tailwind CSS utility-first styling, and canvas-based visual designs. Use when building user interfaces, implementing design systems, creating responsive layouts, adding accessible components (dialogs, dropdowns, forms, tables), customizing themes and colors, implementing dark mode, generating visual designs and posters, or establishing consistent styling patterns across applications.
- **`ui-ux-pro-max`**: UI/UX design intelligence for web, mobile, and desktop. This skill should be used when designing, building, reviewing, or fixing interfaces, including pages, components, design systems, accessibility, interaction, responsive layout, typography, color, charts, and stack-specific UI implementation. Searchable local data: 79 searchable styles (50 active), 192 product palettes and reasoning profiles, 74 font pairings, 119 UX guidelines, 105 icons, 17 GSAP presets, 25 chart types, and 22 stacks.
- **`verification-before-completion`**: Use when about to claim work is complete, fixed, or passing, before committing or creating PRs - requires running verification commands and confirming output before making any success claims; evidence before assertions always
- **`writing-for-agents`**: Writing documents for agents. Use when creating or editing skills, or modifying AGENTS.md or CLAUDE.md.
- **`writing-plans`**: Use when you have a spec or requirements for a multi-step task, before touching code
