import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import agent_team


class TestScaffoldEdgeCasesAndMigrations(unittest.TestCase):
    def setUp(self):
        self._orig_lang = agent_team.CURRENT_LANG

    def tearDown(self):
        agent_team.CURRENT_LANG = self._orig_lang

    def _make_cfg(self, target_dir: Path, lang: str = "en") -> agent_team.TeamConfig:
        agent_team.CURRENT_LANG = lang
        cfg = agent_team.build_preset_config(
            target_dir,
            "",
            "",
            ["agy", "codex", "claude"],
            ["core-subagents-tdd"],
            "json-only",
        )
        cfg.add_commit_restrictions = True
        return cfg

    def test_custom_agents_md_without_managed_headings_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._make_cfg(Path(tmp), "en")
            custom_md = (
                "# Acme Payments Service\n\n"
                "## Build & Test Commands\n"
                "- Run `make check` before opening PRs.\n"
                "- Never touch `migrations/0001_init.sql`.\n"
            )
            merged = agent_team.build_root_agents_md(cfg, existing_content=custom_md)
            self.assertLessEqual(len(merged.splitlines()), agent_team.MAX_AGENTS_MD_LINES)
            self.assertIn("# Acme Payments Service", merged)
            self.assertIn("Run `make check` before opening PRs.", merged)
            self.assertIn("Never touch `migrations/0001_init.sql`.", merged)
            self.assertIn("## Team Topology & Delegation Rules", merged)
            self.assertIn("## Agent-Specific Instructions", merged)
            self.assertIn("`designer`", merged)
            self.assertEqual(merged.count("## Agent-Specific Instructions"), 1)

    def test_existing_agents_md_with_both_headings_updates_in_place_without_duplication(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._make_cfg(Path(tmp), "en")
            stale_existing = (
                "# Repository & Agent Guidelines — demo\n\n"
                "## Custom Architecture Notes\n"
                "- Hexagonal ports live in `src/ports/`.\n\n"
                "## Team Topology & Delegation Rules\n\n"
                "### Phase 2: Hierarchical Execution (Orchestrator + Sub-agents)\n"
                "- `orchestrator`: Old 7-role topology missing designer.\n"
                "- `implementer`: Old implementer line.\n\n"
                "## Agent-Specific Instructions\n\n"
                "- Old instruction\n"
            )
            updated = agent_team.build_root_agents_md(cfg, existing_content=stale_existing)
            self.assertLessEqual(len(updated.splitlines()), agent_team.MAX_AGENTS_MD_LINES)
            self.assertIn("Hexagonal ports live in `src/ports/`.", updated)
            self.assertNotIn("Old 7-role topology missing designer.", updated)
            self.assertIn("- `designer`:", updated)
            self.assertEqual(updated.count("## Team Topology & Delegation Rules"), 1)
            self.assertEqual(updated.count("## Agent-Specific Instructions"), 1)
            self.assertEqual(updated.count("Execution & Concurrency Contract"), 1)

            # Idempotency on second run
            updated_twice = agent_team.build_root_agents_md(cfg, existing_content=updated)
            self.assertEqual(updated, updated_twice)

    def test_over_limit_existing_agents_md_raises_and_leaves_disk_file_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cfg = self._make_cfg(tmp_path, "en")
            over_limit_lines = ["# Custom Monorepo Guide", "", "## Domain Invariants"] + [
                f"- Invariant rule #{i}: keep bounded context isolated." for i in range(1, 135)
            ]
            over_limit_md = "\n".join(over_limit_lines) + "\n"
            agents_path = tmp_path / "AGENTS.md"
            agents_path.write_text(over_limit_md, encoding="utf-8")

            with self.assertRaises(ValueError) as ctx:
                agent_team.build_root_agents_md(cfg, existing_content=over_limit_md)
            self.assertIn(".agents/README.md", str(ctx.exception))

            with self.assertRaises(ValueError):
                agent_team.write_project_configuration(cfg, dry_run=False)

            self.assertEqual(
                agents_path.read_text(encoding="utf-8"),
                over_limit_md,
                "Existing AGENTS.md on disk must remain byte-for-byte untouched on overflow",
            )
            self.assertFalse(
                (tmp_path / ".agents" / "README.md").exists(),
                "Overflow check must fail before writing partial scaffold files",
            )

    def test_claude_orchestrator_has_canonical_agent_tool_without_write_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._make_cfg(Path(tmp), "en")
            orch = next(a for a in cfg.agents if a.id == "orchestrator")
            orch_md = agent_team.build_claude_agent_md(cfg, orch)
            self.assertIn("tools: Read, Grep, Glob, Bash, Agent", orch_md)
            self.assertNotIn("Edit", orch_md)
            self.assertNotIn("Write", orch_md)

            for writer_id in ("implementer", "designer"):
                writer = next(a for a in cfg.agents if a.id == writer_id)
                writer_md = agent_team.build_claude_agent_md(cfg, writer)
                self.assertIn("tools: Read, Edit, Write, Bash, Grep, Glob", writer_md)
                self.assertNotIn(", Agent", writer_md)

    def test_agy_cli_and_ide_tool_grants_respect_write_boundary(self):
        disallowed_write = {
            "edit_file",
            "write_file",
            "write_to_file",
            "replace_file_content",
            "multi_replace_file_content",
        }
        with tempfile.TemporaryDirectory() as tmp:
            cfg = self._make_cfg(Path(tmp), "en")
            for ag in cfg.agents:
                if ag.enable_write:
                    for t in ("read_file", "edit_file", "write_file", "run_command", "manage_task"):
                        self.assertIn(t, ag.agy_tools, f"{ag.id} missing CLI tool {t}")
                else:
                    self.assertIn("read_file", ag.agy_tools, f"{ag.id} missing CLI read_file")
                    self.assertIn("run_command", ag.agy_tools, f"{ag.id} missing run_command for graphify/checks")
                    for wt in disallowed_write:
                        self.assertNotIn(wt, ag.agy_tools, f"{ag.id} leaked write tool {wt}")

    def test_write_project_configuration_preserves_existing_commit_restrictions_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cfg = self._make_cfg(tmp_path, "en")
            rule_path = tmp_path / ".agents" / "rules" / "commit-restrictions.md"
            rule_path.parent.mkdir(parents=True, exist_ok=True)
            custom_rule = "# Custom Commit Restrictions\n- NEVER commit `secrets.env` or `AGENTS.md`.\n"
            rule_path.write_text(custom_rule, encoding="utf-8")

            agent_team.write_project_configuration(cfg, dry_run=False)
            self.assertEqual(
                rule_path.read_text(encoding="utf-8"),
                custom_rule,
                "Existing customized commit-restrictions.md must not be overwritten",
            )

    def test_load_team_config_upgrades_only_unmodified_legacy_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            agents_dir = tmp_path / ".agents"
            agents_dir.mkdir(parents=True, exist_ok=True)

            legacy_orch_mission = (
                "Receive the finalized architecture blueprint approved from the 2-round lead debate (lead-architect ⮂ lead-critic). "
                "Coordinate execution by dispatching searcher for codebase scouting, implementer for TDD coding, reviewer for independent "
                "code review, and committer for Conventional Commits. Verify overall integration without modifying production code directly."
            )
            legacy_orch_criteria = (
                "Zero overlapping file ownership across subagents; all reviewer findings resolved; "
                "full application builds and passes tests before claiming completion."
            )
            legacy_rw_tools = [
                "run_command",
                "view_file",
                "write_to_file",
                "replace_file_content",
                "multi_replace_file_content",
                "grep_search",
                "find_by_name",
                "list_dir",
            ]

            raw_cfg = {
                "project_name": "demo",
                "project_path": str(tmp_path),
                "tech_stack": "Python",
                "project_context": "Demo context",
                "project_goal": "Demo goal",
                "extra_rules": ["graphify"],
                "harnesses": ["agy", "codex", "claude"],
                "skill_apply_mode": "json-only",
                "add_commit_restrictions": True,
                "selected_skill_bundles": [],
                "selected_skills": [],
                "agents": [
                    {
                        "id": "orchestrator",
                        "title": "Orch",
                        "role": "Lead Execution Orchestrator",
                        "mission": legacy_orch_mission,
                        "provider": "multi",
                        "agy_model": "gemini-4-argon-high",
                        "claude_model": "claude-opus-5-5-medium",
                        "codex_model": "gpt-6-astra",
                        "reasoning_effort": "high",
                        "context_scope": "Scope",
                        "goal_criteria": legacy_orch_criteria,
                        "enable_write": False,
                        "enable_subagents": True,
                        "enable_mcp": True,
                        "workspace_mode": "inherit",
                        "agy_tools": list(legacy_rw_tools),
                        "skills": ["subagent-driven-development"],
                        "fallback_chain": ["agy:gemini-4-argon-high"],
                    },
                    {
                        "id": "reviewer",
                        "title": "Custom Reviewer",
                        "role": "Custom Reviewer",
                        "mission": "USER CUSTOMIZED MISSION — DO NOT OVERWRITE",
                        "provider": "multi",
                        "agy_model": "gemini-3.1-pro-high",
                        "claude_model": "sonnet",
                        "codex_model": "gpt-6.1-sol",
                        "reasoning_effort": "xhigh",
                        "context_scope": "Scope",
                        "goal_criteria": "USER CUSTOMIZED CRITERIA",
                        "enable_write": False,
                        "enable_subagents": False,
                        "enable_mcp": False,
                        "workspace_mode": "inherit",
                        "agy_tools": ["custom_tool_alpha"],
                        "skills": ["code-review"],
                        "fallback_chain": ["agy:gemini-3.1-pro-high"],
                    },
                ],
            }
            (agents_dir / "team-config.json").write_text(json.dumps(raw_cfg), encoding="utf-8")

            agent_team.CURRENT_LANG = "en"
            loaded = agent_team._load_team_config_from_disk(tmp_path)
            self.assertIsNotNone(loaded)
            orch = next(a for a in loaded.agents if a.id == "orchestrator")
            self.assertIn("designer", orch.mission)
            self.assertIn("invoke_subagent", orch.agy_tools)
            self.assertNotIn("write_to_file", orch.agy_tools)

            rev = next(a for a in loaded.agents if a.id == "reviewer")
            self.assertEqual(rev.mission, "USER CUSTOMIZED MISSION — DO NOT OVERWRITE")
            self.assertEqual(rev.goal_criteria, "USER CUSTOMIZED CRITERIA")
            self.assertEqual(rev.agy_tools, ["custom_tool_alpha"])


if __name__ == "__main__":
    unittest.main()
