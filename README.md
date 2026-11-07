<div align="center">
  <img src="./assets/demo.gif" alt="agt (agent-team) — Multi-Agent CLI Demo" width="100%" />
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

`agt` (`agent-team`) is an interactive, zero-dependency CLI tool that scaffolds a coordinated **2-Phase 8-Role AI Team** (**lead-architect**, **lead-critic**, **orchestrator**, **reviewer**, **designer**, **implementer**, **searcher**, **committer**) across **Google Antigravity (`agy`)**, **OpenAI Codex (`codex`)**, and **Anthropic Claude Code (`claude`)** while strictly maintaining `AGENTS.md` **under 150 lines**.

---

## ⚡ 10-Second Quick Install

Install `agt` into `~/.local/bin/agt` with a single command (requires Python 3.10+):

```bash
curl -fsSL https://raw.githubusercontent.com/rcryan-hniht/agent-team/main/install.sh | bash
```

---

## 🎮 Essential Commands

| Command | Purpose |
| :--- | :--- |
| `agt` | Open interactive TUI setup wizard & project manager (`--lang vi` for Tiếng Việt) |
| `agt init -y` | Fast one-command preset bootstrap for the standard 8-role team |
| `agt ps` | Realtime live monitor (fastest 0.5s refresh, nvim `j`/`k` scroll, token sparklines) |
| `agt status` | Inspect current repository active agent roster, models, and linked skills |
| `agt fallback` | Inspect, manage, or step down model fallback chains (`--step-down <role>`) |
| `agt clean -y` | Cleanly remove generated AI agent configs from target repo |

---

## 🤖 The 8-Role Team at a Glance

| Role | Mascot | Default Model (`agy`) | Default Model (`codex`) | Phase | Purpose |
| :--- | :---: | :--- | :--- | :---: | :--- |
| **`lead-architect`** | 🐋 | `gemini-4-argon-high` / `claude-opus-5-5-medium` | `gpt-6-astra` (`high`) | Phase 1 | Strategic solution architecture & RFC proposal |
| **`lead-critic`** | 🐋 | `gemini-3.1-pro-high` / `claude-opus-5-5-medium` | `gpt-6.1-sol` (`xhigh`) | Phase 1 | 2-round technical stress-testing & YAGNI verification |
| **`orchestrator`** | 🐙 | `gemini-4-argon-high` / `claude-opus-5-5-medium` | `gpt-6-astra` (`high`) | Phase 2 | Execution coordination & task delegation |
| **`reviewer`** | 🦈 | `gemini-3.1-pro-high` | `gpt-6.1-sol` (`xhigh`) | Phase 2 | Independent 2-axis quality & security review |
| **`designer`** | 🐧 | `gemini-3.8-flash-high` | `gpt-6-sol` (`xhigh`) | Phase 2 | UI/UX & Anti-Slop visual styling adhering to design rules |
| **`implementer`** | 🦈 | `gemini-3.8-flash-high` | `gpt-6-sol` (`xhigh`) | Phase 2 | Minimal TDD implementation & test execution |
| **`searcher`** | 🐟 | `gemini-3.8-flash-medium` | `gpt-6-luna` (`medium`) | Phase 2 | Primary documentation & codebase scout |
| **`committer`** | ⭐ | `gemini-3.7-flash` | `gpt-6-luna` (`low`) | Phase 2 | Atomic Conventional Git Commits |

---

## 💡 Key Highlights

- **Auto-Sync System Theme**: Mascot pixel art and active badges dynamically adapt to Dark/Light system themes (cool neon glow in dark mode, warm Rosewood Garnet pink/red in light mode).
- **Sub-Second Live Telemetry (`agt ps`)**: Default **0.5s** refresh rate with atomic double-buffering (zero flicker), nvim scrolling keys (`j`/`k`/`d`/`u`), and live 15-minute rolling token velocity sparklines `[ ▂▃▄▅▆▇█]`.
- **Strict Context Window Budget**: Keeps root `AGENTS.md` strictly under 150 lines, delegating detailed tables to `.agents/README.md`.
- **Host-Native Orchestration**: Pure multi-harness scaffold and generator (agy, codex, claude); introduces zero custom daemon or runtime overhead.
- **Model Fallback Chains**: Seamless cross-provider failover (`agt fallback --step-down <role>`) when a model hits quota or rate limits.

---

## 📂 Compact Workspace Footprint

```text
<project-root>/
├── AGENTS.md             # Strict universal instructions (< 150 lines)
├── CLAUDE.md             # Claude Code entrypoint (points to @AGENTS.md)
├── .agents/
│   ├── README.md         # Full role-to-model table & skills catalog
│   ├── agents.json       # Subagent registry for Antigravity (agy)
│   ├── skills.json       # Scoped skill discovery manifest
│   ├── agents/           # Role specs (agent.md, agent.toml)
│   ├── subagents/        # Payloads for define_subagent / invoke_subagent
│   └── skills/           # Symlinked local skills
├── .claude/agents/       # Claude Code subagents
└── .codex/config.toml    # OpenAI Codex multi-agent config
```

---

## 🔗 Related Ecosystem Projects

- [`wshobson/agents`](https://github.com/wshobson/agents) — Multi-harness agent & plugin collection.
- [`obra/superpowers`](https://github.com/obra/superpowers) — Agentic development skills (`brainstorming`, `writing-plans`, `subagent-driven-development`).
- [`mattpocock/skills`](https://github.com/mattpocock/skills) — Deep module design, TDD, two-axis `code-review`.
- [`VoltAgent/awesome-claude-code-subagents`](https://github.com/VoltAgent/awesome-claude-code-subagents) — Curated `.claude/agents/` templates.
- [`intellectronica/ruler`](https://github.com/intellectronica/ruler) — Cross-tool rules synchronization.

---

## 📄 License

Released under the [MIT License](./LICENSE).
