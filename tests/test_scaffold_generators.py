import os
import sys
import unittest
import unittest.mock
from pathlib import Path

# Ensure agent-team is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import agent_team


class TestScaffoldGenerators(unittest.TestCase):
    def setUp(self):
        self._orig_lang = agent_team.CURRENT_LANG

    def tearDown(self):
        agent_team.CURRENT_LANG = self._orig_lang

    def _get_preset_cfg(self, lang="en"):
        agent_team.CURRENT_LANG = lang
        return agent_team.build_preset_config(
            Path("/tmp/demo-proj"),
            "",
            "",
            ["agy", "codex", "claude"],
            ["core-subagents-tdd"],
            "json-only",
        )

    def test_pure_scaffold_no_custom_runtime(self):
        """
        Verify agent_team defines all 8 default roles and adds NO custom runtime/daemon
        execution subcommands beyond standard scaffold management.
        """
        expected_roles = [
            "lead-architect",
            "lead-critic",
            "orchestrator",
            "reviewer",
            "designer",
            "implementer",
            "searcher",
            "committer",
        ]
        self.assertEqual(list(agent_team.DEFAULT_AGENT_TEMPLATES_EN.keys()), expected_roles)
        self.assertEqual(list(agent_team.DEFAULT_AGENT_TEMPLATES_VI.keys()), expected_roles)

        # Inspect CLI parser to ensure zero custom execution/daemon runtime subcommands
        parser = agent_team.build_cli_parser()
        # Find subparser action
        subparsers_action = None
        for action in parser._actions:
            if isinstance(action, getattr(unittest.mock, "MagicMock", object)):
                continue
            if type(action).__name__ == "_SubParsersAction":
                subparsers_action = action
                break

        self.assertIsNotNone(subparsers_action, "CLI must have subparsers")
        registered_subcommands = set(subparsers_action.choices.keys())
        # Standard administrative subcommands only
        disallowed_runtime_commands = {"run", "serve", "daemon", "execute", "start-runtime", "worker", "runtime"}
        for cmd in disallowed_runtime_commands:
            self.assertNotIn(cmd, registered_subcommands, f"Custom runtime command '{cmd}' should not exist")

    def test_orchestrator_has_no_write_tools_and_has_subagent_tools(self):
        """
        Verify orchestrator template in both EN and VI has enable_write=False, enable_subagents=True,
        has Antigravity 2.0 canonical subagent/inspection tools, and absolutely NO write tools or legacy aliases
        in agy_tools or build_single_agent_md.
        Verify mission mentions designer and concurrency ordering.
        """
        disallowed_write_tools = {
            "write_to_file",
            "replace_file_content",
            "multi_replace_file_content",
            "write_file",
            "edit_file",
        }
        legacy_conflict_aliases = {
            "view_file",
            "grep_search",
            "find_by_name",
            "list_dir",
            "write_to_file",
            "replace_file_content",
            "multi_replace_file_content",
            "read_url_content",
        }
        canonical_orchestrator_tools = [
            "read_file",
            "run_command",
            "manage_task",
            "invoke_subagent",
            "send_message",
            "manage_subagents",
            "define_subagent",
        ]

        for lang in ("en", "vi"):
            templates = (
                agent_team.DEFAULT_AGENT_TEMPLATES_VI if lang == "vi" else agent_team.DEFAULT_AGENT_TEMPLATES_EN
            )
            orch_tpl = templates["orchestrator"]
            self.assertFalse(orch_tpl["enable_write"], f"orchestrator [{lang}] must have enable_write=False")
            self.assertTrue(orch_tpl["enable_subagents"], f"orchestrator [{lang}] must have enable_subagents=True")

            for t in canonical_orchestrator_tools:
                self.assertIn(t, orch_tpl["agy_tools"], f"orchestrator [{lang}] agy_tools missing canonical tool '{t}'")

            for wt in disallowed_write_tools:
                self.assertNotIn(wt, orch_tpl["agy_tools"], f"orchestrator [{lang}] agy_tools contains write tool '{wt}'")

            for at in legacy_conflict_aliases:
                self.assertNotIn(at, orch_tpl["agy_tools"], f"orchestrator [{lang}] agy_tools contains legacy conflict alias '{at}'")

            # Check mission mentions designer and ordering / fan-out
            mission = orch_tpl["mission"]
            self.assertIn("designer", mission, f"orchestrator [{lang}] mission should mention 'designer'")
            if lang == "en":
                self.assertTrue(
                    any(k in mission.lower() for k in ("fan-out", "parallel")),
                    "orchestrator [en] mission should mention fan-out / parallel reads",
                )
            else:
                self.assertTrue(
                    any(k in mission.lower() for k in ("fan-out", "song song")),
                    "orchestrator [vi] mission should mention fan-out / song song reads",
                )

            # Check build_single_agent_md output
            cfg = self._get_preset_cfg(lang)
            orch_spec = next(a for a in cfg.agents if a.id == "orchestrator")
            md_output = agent_team.build_single_agent_md(cfg, orch_spec)
            for wt in disallowed_write_tools:
                self.assertNotIn(wt, md_output, f"build_single_agent_md(orchestrator) [{lang}] leaked write tool '{wt}'")
            for t in canonical_orchestrator_tools:
                self.assertIn(t, md_output, f"build_single_agent_md(orchestrator) [{lang}] missing canonical tool '{t}'")
            for at in legacy_conflict_aliases:
                self.assertNotIn(at, md_output, f"build_single_agent_md(orchestrator) [{lang}] contains legacy conflict alias '{at}'")

    def test_implementer_and_designer_retain_write_tools(self):
        """
        Verify implementer and designer templates retain enable_write=True and Antigravity 2.0 canonical write tools.
        """
        required_canonical_write_tools = ["read_file", "edit_file", "write_file", "run_command", "manage_task"]
        for lang in ("en", "vi"):
            cfg = self._get_preset_cfg(lang)
            for role_id in ("implementer", "designer"):
                spec = next(a for a in cfg.agents if a.id == role_id)
                self.assertTrue(spec.enable_write, f"{role_id} [{lang}] must have enable_write=True")
                for wt in required_canonical_write_tools:
                    self.assertIn(wt, spec.agy_tools, f"{role_id} [{lang}] must contain '{wt}' in agy_tools")

    def test_antigravity_canonical_tools_no_alias_conflicts_or_duplicates_across_all_roles(self):
        """
        Anti-regression: Ensure generated agent.md for EVERY role contains zero duplicate tools
        and zero legacy aliases that conflict with Antigravity 2.0 canonical tool resolution.
        """
        legacy_conflict_aliases = {
            "view_file",
            "grep_search",
            "find_by_name",
            "list_dir",
            "write_to_file",
            "replace_file_content",
            "multi_replace_file_content",
            "read_url_content",
        }
        for lang in ("en", "vi"):
            cfg = self._get_preset_cfg(lang)
            for ag in cfg.agents:
                md_output = agent_team.build_single_agent_md(cfg, ag)
                lines = md_output.splitlines()
                in_frontmatter = False
                in_tools = False
                tools_in_yaml: List[str] = []
                for line in lines:
                    if line.strip() == "---":
                        if in_frontmatter:
                            break
                        in_frontmatter = True
                        continue
                    if in_frontmatter:
                        if line.startswith("tools:"):
                            in_tools = True
                            continue
                        if in_tools:
                            if line.startswith("  - "):
                                tools_in_yaml.append(line[4:].strip())
                            elif line.startswith(("- ", "name:", "model:", "description:", "mainAgent:", "subagent:")):
                                in_tools = False

                self.assertTrue(tools_in_yaml, f"agent.md for {ag.id} [{lang}] must declare tools in frontmatter")
                self.assertEqual(
                    len(tools_in_yaml),
                    len(set(tools_in_yaml)),
                    f"agent.md for {ag.id} [{lang}] contains duplicate tools: {tools_in_yaml}",
                )
                for alias in legacy_conflict_aliases:
                    self.assertNotIn(
                        alias,
                        tools_in_yaml,
                        f"agent.md for {ag.id} [{lang}] contains legacy conflict alias '{alias}'",
                    )
                self.assertFalse(
                    "read_file" in tools_in_yaml and "view_file" in tools_in_yaml,
                    f"agent.md for {ag.id} [{lang}] contains both read_file and view_file",
                )

    def test_main_agent_flag_hierarchy(self):
        """
        Verify build_single_agent_md generates mainAgent: true ONLY for lead-architect and orchestrator,
        and mainAgent: false for all other 6 roles. All 8 roles must have subagent: true.
        """
        for lang in ("en", "vi"):
            cfg = self._get_preset_cfg(lang)
            for ag in cfg.agents:
                md = agent_team.build_single_agent_md(cfg, ag)
                self.assertIn("subagent: true", md, f"{ag.id} [{lang}] must have subagent: true")
                if ag.id in ("lead-architect", "orchestrator"):
                    self.assertIn(
                        "mainAgent: true",
                        md,
                        f"{ag.id} [{lang}] must have mainAgent: true",
                    )
                    self.assertNotIn(
                        "mainAgent: false",
                        md,
                        f"{ag.id} [{lang}] should not have mainAgent: false",
                    )
                else:
                    self.assertIn(
                        "mainAgent: false",
                        md,
                        f"{ag.id} [{lang}] must have mainAgent: false",
                    )
                    self.assertNotIn(
                        "mainAgent: true",
                        md,
                        f"{ag.id} [{lang}] should not have mainAgent: true",
                    )

    def test_root_agents_md_strict_line_budget_roles_and_contracts(self):
        """
        Verify build_root_agents_md generates strictly < 150 lines (<= 148 lines) for fresh and update,
        both EN and VI, includes all 8 role IDs, designer in topology, and execution contracts.
        """
        for lang in ("en", "vi"):
            cfg = self._get_preset_cfg(lang)

            # Fresh generation
            fresh = agent_team.build_root_agents_md(cfg)
            lines_fresh = fresh.splitlines()
            self.assertLess(
                len(lines_fresh),
                150,
                f"Fresh AGENTS.md [{lang}] lines ({len(lines_fresh)}) must be < 150",
            )
            self.assertLessEqual(
                len(lines_fresh),
                148,
                f"Fresh AGENTS.md [{lang}] lines ({len(lines_fresh)}) should be <= 148",
            )

            # Check 8 role IDs are present
            for ag in cfg.agents:
                self.assertIn(f"`{ag.id}`", fresh, f"Fresh AGENTS.md [{lang}] missing `{ag.id}`")

            # Check designer is in Team Topology Phase 2
            self.assertIn("`designer`", fresh, f"Fresh AGENTS.md [{lang}] missing `designer` in Phase 2")

            # Check contract keywords: host-native, fan-out read, serial write/verify/commit, workflow graph boundary
            self.assertTrue(
                any(k in fresh for k in ("Host-Native", "native", "orchestration")),
                f"Fresh AGENTS.md [{lang}] missing host-native orchestration reference",
            )
            self.assertTrue(
                any(k in fresh.lower() for k in ("fan-out", "song song")),
                f"Fresh AGENTS.md [{lang}] missing fan-out reference",
            )
            self.assertTrue(
                any(k in fresh.lower() for k in ("workflow graph", "gate")),
                f"Fresh AGENTS.md [{lang}] missing workflow graph decision boundary reference",
            )

            # Update existing content
            existing = (
                "# Custom Project Header\n\n"
                "## Project Structure\n"
                "- src/: source files\n\n"
                "## Agent-Specific Instructions\n"
                "- Old bullet 1\n"
                "- Old bullet 2\n"
            )
            updated = agent_team.build_root_agents_md(cfg, existing_content=existing)
            lines_updated = updated.splitlines()
            self.assertLess(
                len(lines_updated),
                150,
                f"Updated AGENTS.md [{lang}] lines ({len(lines_updated)}) must be < 150",
            )
            self.assertIn("Execution", updated, f"Updated AGENTS.md [{lang}] must have Execution Contract bullet")

    def test_agents_readme_md_architecture_and_boundary(self):
        """
        Verify build_agents_readme_md includes all 8 roles, Host-Native Orchestration (agy, codex, claude),
        Execution Concurrency & Ordering Contract, Workflow Graph Decision Boundary (gates, state, retries),
        and asserts NO Saga or hardware security key mentions.
        """
        for lang in ("en", "vi"):
            cfg = self._get_preset_cfg(lang)
            readme = agent_team.build_agents_readme_md(cfg)

            # Check 8 roles
            for ag in cfg.agents:
                self.assertIn(f"`{ag.id}`", readme, f".agents/README.md [{lang}] missing `{ag.id}`")

            # Check Host-Native Orchestration
            self.assertTrue(
                "Host-Native Orchestration" in readme or "Điều Phối Host-Native" in readme,
                f".agents/README.md [{lang}] missing Host-Native Orchestration section",
            )
            self.assertIn("agy", readme)
            self.assertIn("codex", readme)
            self.assertIn("claude", readme)

            # Check Concurrency & Ordering Contract
            self.assertTrue(
                "Concurrency & Ordering Contract" in readme or "Giao Thức Thực Thi" in readme or "Thứ Tự Thực Thi" in readme,
                f".agents/README.md [{lang}] missing Concurrency & Ordering section",
            )
            self.assertTrue(
                any(k in readme.lower() for k in ("fan-out", "song song")),
                f".agents/README.md [{lang}] missing fan-out read mention",
            )
            self.assertTrue(
                "single-writer" in readme.lower() or "đơn ghi" in readme.lower(),
                f".agents/README.md [{lang}] missing single-writer mention",
            )

            # Check Workflow Graph Decision Boundary
            self.assertTrue(
                "Workflow Graph Decision Boundary" in readme or "Ranh Giới Quyết Định Workflow Graph" in readme,
                f".agents/README.md [{lang}] missing Workflow Graph Decision Boundary section",
            )
            self.assertTrue(
                any(k in readme.lower() for k in ("gate", "cổng")),
                f".agents/README.md [{lang}] missing gate mention",
            )
            self.assertTrue(
                any(k in readme.lower() for k in ("checkpoint", "khôi phục state", "lưu/khôi phục")),
                f".agents/README.md [{lang}] missing state checkpoint/restore mention",
            )
            self.assertTrue(
                any(k in readme.lower() for k in ("retry", "thử lại")),
                f".agents/README.md [{lang}] missing retry mention",
            )

            # Assert negative constraints
            self.assertNotIn("Saga", readme, f".agents/README.md [{lang}] should not contain 'Saga'")
            self.assertNotIn(
                "hardware security key",
                readme,
                f".agents/README.md [{lang}] should not contain 'hardware security key'",
            )

    def test_team_orchestrator_skill_roster_and_contracts(self):
        """
        Verify build_team_orchestrator_skill includes all 8 roles (designer), host-native orchestration
        across 3 harnesses, parallel read fan-out, serialized shared-file write -> verify -> commit,
        and workflow graph boundary.
        """
        for lang in ("en", "vi"):
            cfg = self._get_preset_cfg(lang)
            skill = agent_team.build_team_orchestrator_skill(cfg)

            # 8 roles present
            for ag in cfg.agents:
                self.assertIn(f"`{ag.id}`", skill, f"team-orchestrator SKILL.md [{lang}] missing `{ag.id}`")

            # Native orchestration on 3 harnesses
            self.assertIn("agy", skill)
            self.assertIn("codex", skill)
            self.assertIn("claude", skill)

            # Fan-out read and serialized shared-file edits
            self.assertTrue(
                any(k in skill.lower() for k in ("fan-out", "song song")),
                f"team-orchestrator SKILL.md [{lang}] missing fan-out mention",
            )
            self.assertTrue(
                any(k in skill.lower() for k in ("tuần tự", "ordered", "sequential")),
                f"team-orchestrator SKILL.md [{lang}] missing sequential/ordered write mention",
            )

            # Workflow graph decision boundary
            self.assertTrue(
                any(k in skill.lower() for k in ("workflow graph", "gate", "cổng chặn")),
                f"team-orchestrator SKILL.md [{lang}] missing workflow graph boundary mention",
            )

    def test_codex_and_claude_scaffold_alignment(self):
        """
        Verify build_codex_config_toml has 8 [agents.<id>] blocks and developer_instructions mentions designer,
        fan-out read, serialized shared-file edits/review/commit, and workflow graph boundary.
        Verify build_claude_agent_md tool assignments.
        """
        for lang in ("en", "vi"):
            cfg = self._get_preset_cfg(lang)

            # Codex config
            toml = agent_team.build_codex_config_toml(cfg)
            for ag in cfg.agents:
                self.assertIn(f"[agents.{ag.id}]", toml, f".codex/config.toml [{lang}] missing [agents.{ag.id}]")

            self.assertIn("designer", toml, f".codex/config.toml [{lang}] developer_instructions missing designer")
            self.assertTrue(
                any(k in toml.lower() for k in ("fan-out", "parallel")),
                f".codex/config.toml [{lang}] developer_instructions missing fan-out read",
            )
            self.assertTrue(
                any(k in toml.lower() for k in ("workflow graph", "gate")),
                f".codex/config.toml [{lang}] developer_instructions missing workflow graph boundary",
            )

            # Claude agent md
            orch_spec = next(a for a in cfg.agents if a.id == "orchestrator")
            claude_orch = agent_team.build_claude_agent_md(cfg, orch_spec)
            self.assertIn("tools: Read, Grep, Glob, Bash, Agent", claude_orch)
            self.assertNotIn("Edit", claude_orch)
            self.assertNotIn("Write", claude_orch)

            impl_spec = next(a for a in cfg.agents if a.id == "implementer")
            claude_impl = agent_team.build_claude_agent_md(cfg, impl_spec)
            self.assertIn("Edit", claude_impl)
            self.assertIn("Write", claude_impl)

            des_spec = next(a for a in cfg.agents if a.id == "designer")
            claude_des = agent_team.build_claude_agent_md(cfg, des_spec)
            self.assertIn("Edit", claude_des)
            self.assertIn("Write", claude_des)


if __name__ == "__main__":
    unittest.main()
