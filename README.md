<div align="center">
  <img src="./assets/banner.svg" alt="agt (agent-team) — Multi-Agent Team & Skills CLI Generator Banner" width="100%" />
  <br />
  <br />
  <p>
    <strong>English</strong> | <a href="./README-vi.md">Tiếng Việt</a>
  </p>
  <p>
    <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-00F0FF.svg?style=flat-square&labelColor=0D1117" alt="License: MIT" /></a>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-10B981.svg?style=flat-square&labelColor=0D1117" alt="Python 3.10+" /></a>
    <img src="https://img.shields.io/badge/AGENTS.md-%3C%20150%20Lines-F59E0B.svg?style=flat-square&labelColor=0D1117" alt="AGENTS.md < 150 Lines" />
    <img src="https://img.shields.io/badge/Harnesses-.agents%20%7C%20.codex%20%7C%20.claude-38BDF8.svg?style=flat-square&labelColor=0D1117" alt="Harnesses" />
  </p>
</div>

`agt` (`agent-team`) is an interactive, zero-dependency CLI wizard that scaffolds a coordinated **Multi-Agent AI Team** (**Orchestrator**, **Reviewer**, **Implementer**, **Searcher**, **Committer**, or custom specialist roles) for any repository inside your `~/Projects` workspace.

It generates unified, cross-compatible agent definitions and applies local **Skills** across all three major agentic coding harnesses:
- **Google Antigravity (`agy`)**: `AGENTS.md`, `.agents/README.md`, `.agents/agents.json`, `.agents/agents/<role>/agent.md`, `.agents/skills.json`, `.agents/skills/`
- **OpenAI Codex CLI (`codex`)**: `AGENTS.md`, `.codex/config.toml`, `.agents/agents/<role>/agent.toml`
- **Anthropic Claude Code (`claude`)**: `CLAUDE.md`, `.claude/agents/<role>.md`

---

## ✨ Key Features

- **Interactive Multi-Agent Setup Wizard**: Asks step-by-step questions for your project context, primary goals, and each agent's mission, provider, model, reasoning effort, scope, completion criteria, and tool permissions (`Read-Only` vs `Read+Write+Bash`).
- **Strict `< 150 Lines` `AGENTS.md` Budget**: Enforces a hard limit of under 150 lines on root `AGENTS.md` files (preserving existing repository sections while pushing detailed tables into `.agents/README.md`) to prevent context window bloat.
- **Automatic Local Skill Discovery & Linking**: Scans your local skill libraries (`~/.gemini/config/plugins`, `~/Projects/Hephaestus/.agents/skills`, and built-in Antigravity skills) and applies selected skill bundles via `symlink`, `copy`, or `.agents/skills.json`.
- **Bilingual CLI Interface (`English` & `Tiếng Việt`)**: Full English interactive terminal UI by default (`--lang en`), with seamless switching to Vietnamese (`--lang vi` or directly in the dashboard menu).

---

## 🚀 Quick Start

### 1. Installation

Install `agt` into `~/.local/bin/agt` with a single `curl` command:

```bash
curl -fsSL https://raw.githubusercontent.com/rcryan-hniht/agent-team/main/install.sh | bash
```

### 2. Examples

#### A. Launch the Interactive TUI / Wizard
Run `agt` inside your project directory:

```bash
cd ~/project-example
agt
```

Or jump straight into the setup wizard:

```bash
agt init
```

Switch CLI language between Vietnamese (`vi`) and English (`en`):

```bash
agt --lang vi
agt --lang en
```

#### B. One-Command Preset Initialization (Non-Interactive)
Bootstrap the standard 5-agent team (`orchestrator`, `reviewer`, `implementer`, `committer`, `searcher`) with default models and skill bundles:

```bash
agt init --target ~/project-example --yes \
  --goal "Build and verify core features with a 5-agent team"
```

#### C. Inspect Applied Agents, Live Running Tasks & Local Skills
```bash
# Check live running Agent CLI processes, active subagents, and task checklists
agt ps --target ~/project-example

# View the active agent roster, models, and skills in a repository
agt status --target ~/project-example

# List all discovered local skills grouped by plugin/source
agt list-skills
```

---

## 🏗️ Default Agent Roster & Model Mapping

| Role | Workspace Path | Default Model (`agy`) | Default Model (`codex`) | Mode | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`orchestrator`** | `.agents/agents/orchestrator/agent.md` | `gemini-4-argon-high` / `claude-opus-5-5-medium` | `gpt-6-astra` (`high`) | Read/Coord | Architecture, task breakdown, delegation, and final integration verification |
| **`reviewer`** | `.agents/agents/reviewer/agent.md` | `gemini-3.1-pro-high` | `gpt-6.1-sol` (`xhigh`) | Read-Only | Independent code review along Spec Compliance, Security, Async Safety, and Test Quality |
| **`implementer`** | `.agents/agents/implementer/agent.md` | `gemini-3.8-flash-high` | `gpt-6-sol` (`xhigh`) | Read+Write | Minimal complete implementation, TDD (Red-Green-Refactor), and test execution |
| **`searcher`** | `.agents/agents/searcher/agent.md` | `gemini-3.8-flash-medium` | `gpt-6-luna` (`medium`) | Read-Only | Focused research against primary documentation and fast codebase scouting |
| **`committer`** | `.agents/agents/committer/agent.md` | `gemini-3.7-flash` | `gpt-6-luna` (`low`) | Read-Only | Concise, atomic Conventional Commits creation |

---

## 📂 Generated Directory Structure

```text
<project-root>/
├── AGENTS.md                                  # Compact (< 150 lines) universal instructions & context pointers
├── CLAUDE.md                                  # Entrypoint for Anthropic Claude Code (points to @AGENTS.md)
├── .agents/
│   ├── README.md                              # Full role-to-model mapping table & applied skills catalog
│   ├── agents.json                            # Subagent registry for Antigravity CLI (agy)
│   ├── skills.json                            # Scoped skill discovery manifest (include_only)
│   ├── team-config.json                       # Saved wizard state for fast re-configuration
│   ├── rules/
│   │   └── commit-restrictions.md             # Optional guardrail preventing accidental commits of local agent docs
│   ├── agents/
│   │   ├── orchestrator/
│   │   │   ├── agent.md                       # Antigravity subagent definition (YAML frontmatter + prompt)
│   │   │   └── agent.toml                     # OpenAI Codex subagent instructions & reasoning effort
│   │   ├── reviewer/ (agent.md, agent.toml)
│   │   ├── implementer/ (agent.md, agent.toml)
│   │   ├── searcher/ (agent.md, agent.toml)
│   │   └── committer/ (agent.md, agent.toml)
│   └── skills/                                # Symlinked or copied workspace skills
├── .claude/
│   └── agents/
│       ├── orchestrator.md                    # Claude Code subagent definition
│       ├── reviewer.md
│       ├── implementer.md
│       ├── searcher.md
│       └── committer.md
└── .codex/
    └── config.toml                            # OpenAI Codex CLI multi-agent configuration
```

---

## 🔗 Related Open-Source Projects

- [`wshobson/agents`](https://github.com/wshobson/agents) — Multi-harness agent & plugin collection.
- [`obra/superpowers`](https://github.com/obra/superpowers) — Agentic software development workflow skills (`brainstorming`, `writing-plans`, `subagent-driven-development`, `test-driven-development`).
- [`mattpocock/skills`](https://github.com/mattpocock/skills) — Deep module design, TDD, two-axis `code-review`, and `writing-for-agents` skills.
- [`VoltAgent/awesome-claude-code-subagents`](https://github.com/VoltAgent/awesome-claude-code-subagents) — Curated `.claude/agents/` role templates.
- [`intellectronica/ruler`](https://github.com/intellectronica/ruler) — Cross-tool rules synchronization utility.

---

## 📄 License

Released under the [MIT License](./LICENSE).
