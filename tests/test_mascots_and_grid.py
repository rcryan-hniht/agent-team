import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure agent-team is importable
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import agent_team


class TestMascotsAndCatalog(unittest.TestCase):
    def test_eight_roles_and_unique_mascots(self):
        roles = [r[0] for r in agent_team.PIXEL_ART_ANIMALS]
        self.assertEqual(len(roles), 8, f"Expected 8 roles in PIXEL_ART_ANIMALS, got {len(roles)}: {roles}")
        self.assertEqual(roles[0], "lead-architect")
        self.assertEqual(roles[1], "lead-critic")
        self.assertEqual(roles[2], "orchestrator")
        self.assertEqual(roles[3], "reviewer")
        self.assertEqual(roles[4], "designer")
        self.assertEqual(roles[5], "implementer")
        self.assertEqual(roles[6], "searcher")
        self.assertEqual(roles[7], "committer")

        # Animal names EN
        animals = {r[0]: r[2] for r in agent_team.PIXEL_ART_ANIMALS}
        self.assertEqual(animals["lead-architect"], "whale")
        self.assertEqual(animals["implementer"], "hammerhead shark")
        self.assertEqual(animals["designer"], "southern rockhopper penguin")

        # Animal names VI
        self.assertEqual(agent_team.ROLE_ANIMALS_VI.get("lead-architect"), "cá voi")
        self.assertEqual(agent_team.ROLE_ANIMALS_VI.get("implementer"), "cá mập đầu búa")
        self.assertEqual(agent_team.ROLE_ANIMALS_VI.get("designer"), "chim cánh cụt rockhopper phương nam")

        # Mascot emojis
        self.assertEqual(agent_team.MASCOT_EMOJIS.get("lead-architect"), "🐋")
        self.assertEqual(agent_team.MASCOT_EMOJIS.get("implementer"), "🦈")
        self.assertEqual(agent_team.MASCOT_EMOJIS.get("designer"), "🐧")

        # All 8 sprites must be distinct (no 2 sprites identical)
        sprites = [tuple(r[4]) for r in agent_team.PIXEL_ART_ANIMALS]
        self.assertEqual(len(set(sprites)), 8, "Expected all 8 sprites to be unique and distinct")

        # Specifically verify whale, rockhopper penguin, hammerhead shark silhouettes
        whale_sprite = agent_team.PIXEL_ART_ANIMALS[0][4]
        self.assertEqual(whale_sprite[0], ".#.#.", "Whale row 0 should have twin blowhole spray")

        designer_sprite = agent_team.PIXEL_ART_ANIMALS[4][4]
        self.assertEqual(designer_sprite[0], "#...#", "Designer row 0 should have yellow eyebrow crest")
        self.assertEqual(designer_sprite[1], ".###.", "Designer row 1 should have slender round crown")

        hammerhead_sprite = agent_team.PIXEL_ART_ANIMALS[5][4]
        self.assertEqual(hammerhead_sprite[0], "#####", "Hammerhead shark row 0 should have cephalofoil bar")
        self.assertEqual(hammerhead_sprite[1], "#...#", "Hammerhead shark row 1 should have eyes at outer edges")


class TestRoleAliases(unittest.TestCase):
    def test_aliases_mapping(self):
        aliases = agent_team.ROLE_ALIASES
        self.assertEqual(aliases.get("whale"), "lead-architect")
        self.assertEqual(aliases.get("hammerhead"), "implementer")
        self.assertEqual(aliases.get("hammerhead shark"), "implementer")
        self.assertEqual(aliases.get("designer"), "designer")
        self.assertEqual(aliases.get("ui-designer"), "designer")
        self.assertEqual(aliases.get("rockhopper"), "designer")
        self.assertEqual(aliases.get("penguin"), "designer")
        self.assertEqual(aliases.get("southern rockhopper penguin"), "designer")


class TestDetectActiveProvider(unittest.TestCase):
    def test_tier0_override(self):
        with patch.dict(os.environ, {"AGT_PROVIDER": "agy"}, clear=False):
            self.assertEqual(agent_team.detect_active_provider(), "agy")
        with patch.dict(os.environ, {"AGT_PROVIDER": "codex"}, clear=False):
            self.assertEqual(agent_team.detect_active_provider(), "codex")
        with patch.dict(os.environ, {"AGT_PROVIDER": "claude"}, clear=False):
            self.assertEqual(agent_team.detect_active_provider(), "claude")

    def test_tier1_subshell_env(self):
        # Clear AGT_*, ANTIGRAVITY_*, CODEX_*, CLAUDE_*
        base_env = {k: v for k, v in os.environ.items() if not k.startswith(("AGT_", "ANTIGRAVITY_", "CODEX_", "CLAUDE_"))}
        with patch.dict(os.environ, {**base_env, "ANTIGRAVITY_AGENT": "1"}, clear=True):
            self.assertEqual(agent_team.detect_active_provider(), "agy")
        with patch.dict(os.environ, {**base_env, "CODEX_ENV": "1"}, clear=True):
            self.assertEqual(agent_team.detect_active_provider(), "codex")
        with patch.dict(os.environ, {**base_env, "CLAUDE_CODE_ENTRYPOINT": "1"}, clear=True):
            self.assertEqual(agent_team.detect_active_provider(), "claude")


class TestDetectActiveProviders(unittest.TestCase):
    def test_override_can_select_multiple_providers(self):
        with patch.dict(os.environ, {"AGT_PROVIDER": "agy,codex"}, clear=True):
            self.assertEqual(agent_team.detect_active_providers(), {"agy", "codex"})

    def test_project_scan_unions_only_live_in_project_providers(self):
        procs = [
            {"comm": "agy", "cmdline": "agy", "in_project": True},
            {"comm": "codex", "cmdline": "codex", "in_project": True},
            {"comm": "codex", "cmdline": "codex app-server --managed-daemon", "in_project": True},
            {"comm": "claude", "cmdline": "claude", "in_project": False},
            {"comm": "python", "cmdline": "agent_team.py", "in_project": True},
        ]
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(agent_team.Path, "cwd", return_value=Path("/repo/a")),
            patch.object(agent_team.Path, "exists", return_value=False),
            patch.object(agent_team, "get_live_os_procs", return_value=procs),
        ):
            self.assertEqual(agent_team.detect_active_providers(Path("/repo/b")), {"agy", "codex"})

    def test_subshell_environment_counts_when_cwd_matches_target(self):
        with (
            patch.dict(os.environ, {"ANTIGRAVITY_AGENT": "1", "CODEX_ENV": "1"}, clear=True),
            patch.object(agent_team.Path, "cwd", return_value=Path("/repo/b")),
            patch.object(agent_team.Path, "exists", return_value=False),
            patch.object(agent_team, "get_live_os_procs", return_value=[]),
        ):
            self.assertEqual(agent_team.detect_active_providers(Path("/repo/b")), {"agy", "codex"})

    def test_other_repo_environment_and_parent_do_not_leak(self):
        statuses = {
            "/proc/100/status": "Name:\tpython\nPPid:\t101\n",
            "/proc/101/status": "Name:\tagy\nPPid:\t1\n",
        }

        def exists(path):
            return str(path) in {"/proc/100/status", "/proc/101/status"}

        def read_text(path, **kwargs):
            return statuses[str(path)]

        def resolve(path, *args, **kwargs):
            if str(path) == "/proc/101/cwd":
                return Path("/repo/a")
            return path

        with (
            patch.dict(os.environ, {"ANTIGRAVITY_AGENT": "1"}, clear=True),
            patch.object(agent_team.Path, "cwd", return_value=Path("/repo/a")),
            patch.object(agent_team.Path, "exists", autospec=True, side_effect=exists),
            patch.object(agent_team.Path, "read_text", autospec=True, side_effect=read_text),
            patch.object(agent_team.Path, "resolve", autospec=True, side_effect=resolve),
            patch.object(agent_team.os, "getpid", return_value=100),
            patch.object(
                agent_team,
                "get_live_os_procs",
                return_value=[{"comm": "codex", "cmdline": "codex", "in_project": True}],
            ),
        ):
            self.assertEqual(agent_team.detect_active_providers(Path("/repo/b")), {"codex"})

    def test_matching_parent_process_is_counted(self):
        statuses = {
            "/proc/100/status": "Name:\tpython\nPPid:\t101\n",
            "/proc/101/status": "Name:\tcodex\nPPid:\t1\n",
            "/proc/101/comm": "codex\n",
        }

        def exists(path):
            return str(path) in {
                "/proc/100/status",
                "/proc/101/status",
                "/proc/101/comm",
                "/proc/101/cmdline",
            }

        def read_text(path, **kwargs):
            return statuses[str(path)]

        def read_bytes(path):
            return b"codex\x00"

        def resolve(path, *args, **kwargs):
            if str(path) == "/proc/101/cwd":
                return Path("/repo/b")
            return path

        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(agent_team.Path, "cwd", return_value=Path("/repo/a")),
            patch.object(agent_team.Path, "exists", autospec=True, side_effect=exists),
            patch.object(agent_team.Path, "read_text", autospec=True, side_effect=read_text),
            patch.object(agent_team.Path, "read_bytes", autospec=True, side_effect=read_bytes),
            patch.object(agent_team.Path, "resolve", autospec=True, side_effect=resolve),
            patch.object(agent_team.os, "getpid", return_value=100),
            patch.object(agent_team, "get_live_os_procs", return_value=[]),
        ):
            self.assertEqual(agent_team.detect_active_providers(Path("/repo/b")), {"codex"})

    def test_cmd_status_passes_resolved_project_to_grid(self):
        target = Path("/repo/a/../b")
        with (
            patch.object(agent_team.Path, "exists", return_value=False),
            patch.object(agent_team, "render_7col_agent_grid", return_value="grid") as render_grid,
        ):
            agent_team.cmd_status(target)

        render_grid.assert_called_once_with(agents_data=None, project_path=target.resolve())


class TestGridGeometryAndTwoLineMascots(unittest.TestCase):
    def test_render_grid_various_terminal_widths(self):
        for tw in (95, 115, 120, 157, 180):
            # English
            with patch.object(agent_team, "CURRENT_LANG", "en"):
                out_en = agent_team.render_7col_agent_grid(term_w=tw)
                self.assertIn("rockhopper", out_en)
                self.assertIn("penguin", out_en)
                self.assertIn("hammerhead", out_en)
                self.assertIn("shark", out_en)

            # Vietnamese
            with patch.object(agent_team, "CURRENT_LANG", "vi"):
                out_vi = agent_team.render_7col_agent_grid(term_w=tw)
                self.assertIn("cánh cụt", out_vi)
                self.assertIn("rockhopper", out_vi)
                self.assertIn("đầu búa", out_vi)

    def test_render_ps_grid_various_terminal_widths(self):
        for tw in (95, 115, 120, 157, 180):
            with patch.object(agent_team, "CURRENT_LANG", "en"):
                out_en = agent_team.render_7col_agent_ps_grid(term_w=tw)
                self.assertIn("rockhopper", out_en)
                self.assertIn("penguin", out_en)
                self.assertIn("hammerhead", out_en)
                self.assertIn("shark", out_en)

            with patch.object(agent_team, "CURRENT_LANG", "vi"):
                out_vi = agent_team.render_7col_agent_ps_grid(term_w=tw)
                self.assertIn("cánh cụt", out_vi)
                self.assertIn("rockhopper", out_vi)
                self.assertIn("đầu búa", out_vi)


class TestDynamicProviderAccentColors(unittest.TestCase):
    @patch("sys.stdout.isatty", return_value=True)
    def test_agy_active_accent_yellow(self, _mock_isatty):
        with patch.dict(os.environ, {"AGT_PROVIDER": "agy"}):
            grid = agent_team.render_7col_agent_grid(term_w=157)
            lines = grid.splitlines()

            agy_line = next((l for l in lines if "agy:" in l), None)
            codex_line = next((l for l in lines if "codex:" in l), None)
            claude_line = next((l for l in lines if "claude:" in l), None)

            self.assertIsNotNone(agy_line, "agy: line must exist")
            self.assertIsNotNone(codex_line, "codex: line must exist")
            self.assertIsNotNone(claude_line, "claude: line must exist")

            # agy line must have YELLOW (\033[33m) on both label and model values
            self.assertIn("\033[33m", agy_line, "agy: line should contain YELLOW accent color")
            self.assertIn("\033[1m\033[33magy:", agy_line, "agy: header label must be colored YELLOW")

            # codex and claude lines must NOT have YELLOW
            self.assertNotIn("\033[33m", codex_line, "codex: line must NOT contain YELLOW when agy is active")
            self.assertNotIn("\033[33m", claude_line, "claude: line must NOT contain YELLOW when agy is active")

            # Claude row [Write] must NOT use GREEN (\033[32m) because on user Ghostty theme GREEN looks red-orange
            self.assertNotIn("\033[32m", claude_line, "claude: [Write] on inactive row should not be GREEN")

    @patch("sys.stdout.isatty", return_value=True)
    def test_codex_active_accent_yellow(self, _mock_isatty):
        with patch.dict(os.environ, {"AGT_PROVIDER": "codex"}):
            grid = agent_team.render_7col_agent_grid(term_w=157)
            lines = grid.splitlines()

            agy_line = next((l for l in lines if "agy:" in l), None)
            codex_line = next((l for l in lines if "codex:" in l), None)
            claude_line = next((l for l in lines if "claude:" in l), None)

            self.assertIn("\033[33m", codex_line, "codex: line should contain YELLOW when active")
            self.assertIn("\033[1m\033[33mcodex:", codex_line, "codex: header label must be colored YELLOW")
            self.assertNotIn("\033[33m", agy_line, "agy: line must NOT contain YELLOW when codex is active")
            self.assertNotIn("\033[33m", claude_line, "claude: line must NOT contain YELLOW when codex is active")

    @patch("sys.stdout.isatty", return_value=True)
    def test_claude_active_accent_yellow(self, _mock_isatty):
        with patch.dict(os.environ, {"AGT_PROVIDER": "claude"}):
            grid = agent_team.render_7col_agent_grid(term_w=157)
            lines = grid.splitlines()

            agy_line = next((l for l in lines if "agy:" in l), None)
            codex_line = next((l for l in lines if "codex:" in l), None)
            claude_line = next((l for l in lines if "claude:" in l), None)

            self.assertIn("\033[33m", claude_line, "claude: line should contain YELLOW when active")
            self.assertIn("\033[1m\033[33mclaude:", claude_line, "claude: header label must be colored YELLOW")
            self.assertNotIn("\033[33m", agy_line, "agy: line must NOT contain YELLOW when claude is active")
            self.assertNotIn("\033[33m", codex_line, "codex: line must NOT contain YELLOW when claude is active")

    @patch("sys.stdout.isatty", return_value=True)
    def test_multiple_providers_share_active_accent(self, _mock_isatty):
        with patch.dict(os.environ, {"AGT_PROVIDER": "agy,codex"}, clear=True):
            grid = agent_team.render_7col_agent_grid(term_w=157)
        lines = grid.splitlines()
        agy_line = next(l for l in lines if "agy:" in l)
        codex_line = next(l for l in lines if "codex:" in l)
        claude_line = next(l for l in lines if "claude:" in l)

        self.assertIn("\033[33m", agy_line)
        self.assertIn("\033[33m", codex_line)
        self.assertNotIn("\033[33m", claude_line)
        self.assertNotIn("\033[32m", claude_line)


if __name__ == "__main__":
    unittest.main()
