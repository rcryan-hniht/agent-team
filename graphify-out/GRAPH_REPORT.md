# Graph Report - agent-team  (2026-11-08)

## Corpus Check
- 47 files · ~262,047 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: .toml 9, (none) 2)

## Summary
- 382 nodes · 722 edges · 38 communities (18 shown, 20 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 9 edges (avg confidence: 0.85)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ba605fec`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- tr
- TeamConfig
- render_ps_view
- detect_active_providers
- collect_token_telemetry
- demo_runner.py
- README.md
- README-vi.md
- System Prompt
- System Prompt
- System Prompt
- System Prompt
- System Prompt
- System Prompt
- System Prompt
- System Prompt
- agent-team Agents & Skills
- committer/agent.md
- designer/agent.md
- implementer/agent.md
- lead-architect/agent.md
- lead-critic/agent.md
- orchestrator/agent.md
- reviewer/agent.md
- searcher/agent.md
- agents/committer.md
- agents/designer.md
- agents/implementer.md
- agents/lead-architect.md
- agents/lead-critic.md
- agents/orchestrator.md
- agents/reviewer.md
- agents/searcher.md
- install.sh
- record_30s_demo.sh
- smoke_test.sh
- TestScaffoldGenerators

## God Nodes (most connected - your core abstractions)
1. `tr()` - 27 edges
2. `c()` - 22 edges
3. `write_project_configuration()` - 21 edges
4. `render_ps_view()` - 21 edges
5. `TeamConfig` - 20 edges
6. `run_interactive_wizard()` - 18 edges
7. `run_interactive_dashboard()` - 18 edges
8. `render_7col_agent_grid()` - 16 edges
9. `cmd_fallback()` - 15 edges
10. `TestScaffoldGenerators` - 14 edges

## Surprising Connections (you probably didn't know these)
- `build_agents_readme_md()` --calls--> `tr()`  [EXTRACTED]
  agent_team.py → agent_team.py  _Bridges community 0 → community 1_
- `detect_live_agent_occupancy()` --calls--> `tr()`  [EXTRACTED]
  agent_team.py → agent_team.py  _Bridges community 0 → community 2_
- `detect_active_providers()` --calls--> `get_live_os_procs()`  [EXTRACTED]
  agent_team.py → agent_team.py  _Bridges community 3 → community 2_
- `detect_active_providers()` --references--> `Path`  [EXTRACTED]
  agent_team.py →   _Bridges community 3 → community 0_
- `collect_token_telemetry()` --references--> `Path`  [EXTRACTED]
  agent_team.py →   _Bridges community 0 → community 4_

## Import Cycles
- None detected.

## Communities (38 total, 20 thin omitted)

### Community 0 - "tr"
Cohesion: 0.12
Nodes (37): AgentSpec, _apply_fallback_step_to_agent(), ask_choice(), ask_fallback_chain(), ask_multi_choice(), ask_text(), ask_yes_no(), banner() (+29 more)

### Community 1 - "TeamConfig"
Cohesion: 0.07
Nodes (18): apply_skills_to_workspace(), build_agents_json(), build_agents_readme_md(), build_agy_skills_json(), build_claude_agent_md(), build_codex_config_toml(), build_commit_restrictions_rule(), build_root_agents_md() (+10 more)

### Community 2 - "render_ps_view"
Cohesion: 0.06
Nodes (26): _char_width(), _col(), detect_live_agent_occupancy(), detect_system_theme(), format_active_role_desc(), format_token_count(), get_live_os_procs(), _is_vi_text() (+18 more)

### Community 3 - "detect_active_providers"
Cohesion: 0.13
Nodes (8): _classify_proc_provider(), detect_active_provider(), detect_active_providers(), TestDetectActiveProvider, TestDetectActiveProviders, exists(), read_text(), resolve()

### Community 4 - "collect_token_telemetry"
Cohesion: 0.12
Nodes (6): _build_sparkline(), collect_token_telemetry(), _extract_record_tokens(), tail_jsonl_lines(), TokenTelemetrySnapshot, TestTokenTelemetry

### Community 5 - "demo_runner.py"
Cohesion: 0.12
Nodes (6): main(), run_command(), typewriter(), wait_until(), TestMascotsAndCatalog, TestRoleAliases

### Community 6 - "README.md"
Cohesion: 0.25
Nodes (7): ⚡ 10-Second Quick Install, 📂 Compact Workspace Footprint, 🎮 Essential Commands, 💡 Key Highlights, 📄 License, 🔗 Related Ecosystem Projects, 🤖 The 8-Role Team at a Glance

### Community 7 - "README-vi.md"
Cohesion: 0.25
Nodes (7): 📄 Bản quyền (License), ⚡ Cài đặt nhanh trong 10 giây, 🔗 Các dự án mã nguồn mở liên quan, 🎮 Các lệnh thiết yếu, 📂 Cấu trúc thư mục sinh ra, 💡 Điểm nổi bật kỹ thuật, 🤖 Đội ngũ 8 Vai trò & Mascot

### Community 8 - "System Prompt"
Cohesion: 0.29
Nodes (6): 1. Ngữ cảnh Dự án (Project Context), 2. Nhiệm vụ & Phạm vi (Mission & Scope), 3. Tiêu chí Hoàn thành (Completion Criteria), 4. Nguyên tắc Phối hợp Đội ngũ, Antigravity Subagent Spec: `committer` (Conventional Git Committer), System Prompt

### Community 9 - "System Prompt"
Cohesion: 0.29
Nodes (6): 1. Ngữ cảnh Dự án (Project Context), 2. Nhiệm vụ & Phạm vi (Mission & Scope), 3. Tiêu chí Hoàn thành (Completion Criteria), 4. Nguyên tắc Phối hợp Đội ngũ, Antigravity Subagent Spec: `designer` (UI/UX & Anti-Slop Visual Designer), System Prompt

### Community 10 - "System Prompt"
Cohesion: 0.29
Nodes (6): 1. Ngữ cảnh Dự án (Project Context), 2. Nhiệm vụ & Phạm vi (Mission & Scope), 3. Tiêu chí Hoàn thành (Completion Criteria), 4. Nguyên tắc Phối hợp Đội ngũ, Antigravity Subagent Spec: `implementer` (Senior Feature & TDD Implementer), System Prompt

### Community 11 - "System Prompt"
Cohesion: 0.29
Nodes (6): 1. Ngữ cảnh Dự án (Project Context), 2. Nhiệm vụ & Phạm vi (Mission & Scope), 3. Tiêu chí Hoàn thành (Completion Criteria), 4. Nguyên tắc Phối hợp Đội ngũ, Antigravity Subagent Spec: `lead-architect` (Lead Solution Architect & Planner), System Prompt

### Community 12 - "System Prompt"
Cohesion: 0.29
Nodes (6): 1. Ngữ cảnh Dự án (Project Context), 2. Nhiệm vụ & Phạm vi (Mission & Scope), 3. Tiêu chí Hoàn thành (Completion Criteria), 4. Nguyên tắc Phối hợp Đội ngũ, Antigravity Subagent Spec: `lead-critic` (Lead Technical Critic & Challenger), System Prompt

### Community 13 - "System Prompt"
Cohesion: 0.29
Nodes (6): 1. Ngữ cảnh Dự án (Project Context), 2. Nhiệm vụ & Phạm vi (Mission & Scope), 3. Tiêu chí Hoàn thành (Completion Criteria), 4. Nguyên tắc Phối hợp Đội ngũ, Antigravity Subagent Spec: `orchestrator` (Lead Execution Orchestrator), System Prompt

### Community 14 - "System Prompt"
Cohesion: 0.29
Nodes (6): 1. Ngữ cảnh Dự án (Project Context), 2. Nhiệm vụ & Phạm vi (Mission & Scope), 3. Tiêu chí Hoàn thành (Completion Criteria), 4. Nguyên tắc Phối hợp Đội ngũ, Antigravity Subagent Spec: `reviewer` (Independent Code Quality & Security Reviewer), System Prompt

### Community 15 - "System Prompt"
Cohesion: 0.29
Nodes (6): 1. Ngữ cảnh Dự án (Project Context), 2. Nhiệm vụ & Phạm vi (Mission & Scope), 3. Tiêu chí Hoàn thành (Completion Criteria), 4. Nguyên tắc Phối hợp Đội ngũ, Antigravity Subagent Spec: `searcher` (Primary Documentation & Codebase Scout), System Prompt

### Community 16 - "agent-team Agents & Skills"
Cohesion: 0.25
Nodes (7): Agent Roles & Model Mapping, agent-team Agents & Skills, Applied Skills, Execution Concurrency & Ordering Contract, Host-Native Orchestration (Zero Custom Runtime), Project Context & Goal, Workflow Graph Decision Boundary

### Community 39 - "TestScaffoldGenerators"
Cohesion: 0.08
Nodes (5): build_cli_parser(), build_single_agent_md(), canonicalize_antigravity_tools(), _upgrade_legacy_default_agent_fields(), TestScaffoldGenerators

## Knowledge Gaps
- **20 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `detect_active_providers()` connect `detect_active_providers` to `tr`, `render_ps_view`?**
  _High betweenness centrality (0.043) - this node is a cross-community bridge._
- **Should `tr` be split into smaller, more focused modules?**
  _Cohesion score 0.11784511784511785 - nodes in this community are weakly interconnected._
- **Why does `render_7col_agent_grid()` connect `render_ps_view` to `tr`, `detect_active_providers`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Should `TeamConfig` be split into smaller, more focused modules?**
  _Cohesion score 0.07308970099667775 - nodes in this community are weakly interconnected._
- **Why does `build_single_agent_md()` connect `TestScaffoldGenerators` to `tr`, `TeamConfig`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Should `render_ps_view` be split into smaller, more focused modules?**
  _Cohesion score 0.06060606060606061 - nodes in this community are weakly interconnected._
- **Should `detect_active_providers` be split into smaller, more focused modules?**
  _Cohesion score 0.13333333333333333 - nodes in this community are weakly interconnected._