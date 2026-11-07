import itertools
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Tuple
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import agent_team

RGB_SEQ_RE = re.compile(r"\x1b\[38;2;(\d+);(\d+);(\d+)m")


def _extract_rgbs(text: str):
    return [(int(r), int(g), int(b)) for r, g, b in RGB_SEQ_RE.findall(text)]


def _srgb_to_linear(c: int) -> float:
    v = c / 255.0
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def _luminance(r: int, g: int, b: int) -> float:
    return 0.2126 * _srgb_to_linear(r) + 0.7152 * _srgb_to_linear(g) + 0.0722 * _srgb_to_linear(b)


def _contrast_ratio(rgb1: Tuple[int, int, int], rgb2: Tuple[int, int, int]) -> float:
    l1 = _luminance(*rgb1)
    l2 = _luminance(*rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _rgb_to_hsl_saturation(r: int, g: int, b: int) -> float:
    r_n, g_n, b_n = r / 255.0, g / 255.0, b / 255.0
    c_max = max(r_n, g_n, b_n)
    c_min = min(r_n, g_n, b_n)
    delta = c_max - c_min
    if delta == 0:
        return 0.0
    l = (c_max + c_min) / 2.0
    return delta / (1.0 - abs(2.0 * l - 1.0))


class TestSystemThemeAutoSync(unittest.TestCase):
    def test_detect_system_theme_env_and_colorfgbg(self):
        with patch.dict(os.environ, {"AGT_THEME": "light"}, clear=True):
            self.assertEqual(agent_team.detect_system_theme(), "light")
        with patch.dict(os.environ, {"AGT_THEME": "dark"}, clear=True):
            self.assertEqual(agent_team.detect_system_theme(), "dark")
        with patch.dict(os.environ, {"COLORFGBG": "0;15"}, clear=True):
            self.assertEqual(agent_team.detect_system_theme(), "light")
        with patch.dict(os.environ, {"COLORFGBG": "15;0"}, clear=True):
            self.assertEqual(agent_team.detect_system_theme(), "dark")

    def test_detect_system_theme_dms_session_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            dms_dir = home / ".local" / "state" / "DankMaterialShell"
            dms_dir.mkdir(parents=True)
            session_file = dms_dir / "session.json"

            session_file.write_text(json.dumps({"isLightMode": True}), encoding="utf-8")
            with (
                patch.dict(os.environ, {}, clear=True),
                patch.object(agent_team.sys, "platform", "linux"),
                patch.object(agent_team.Path, "home", return_value=home),
            ):
                self.assertEqual(agent_team.detect_system_theme(), "light")

            session_file.write_text(json.dumps({"isLightMode": False}), encoding="utf-8")
            with (
                patch.dict(os.environ, {}, clear=True),
                patch.object(agent_team.sys, "platform", "linux"),
                patch.object(agent_team.Path, "home", return_value=home),
            ):
                self.assertEqual(agent_team.detect_system_theme(), "dark")

    def test_detect_system_theme_linux_gsettings_and_headless_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            for gsettings_out, expected in (
                ("'prefer-dark'\n", "dark"),
                ("'prefer-light'\n", "light"),
                ("'default'\n", "light"),
            ):
                completed = subprocess.CompletedProcess(
                    args=["gsettings"], returncode=0, stdout=gsettings_out, stderr=""
                )
                with (
                    patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-1"}, clear=True),
                    patch.object(agent_team.sys, "platform", "linux"),
                    patch.object(agent_team.Path, "home", return_value=home),
                    patch.object(agent_team.shutil, "which", return_value="/usr/bin/gsettings"),
                    patch("subprocess.run", return_value=completed),
                ):
                    self.assertEqual(agent_team.detect_system_theme(), expected)

            with (
                patch.dict(os.environ, {}, clear=True),
                patch.object(agent_team.sys, "platform", "linux"),
                patch.object(agent_team.Path, "home", return_value=home),
            ):
                self.assertEqual(agent_team.detect_system_theme(), "dark")

    def test_detect_system_theme_macos_defaults(self):
        dark_res = subprocess.CompletedProcess(args=["defaults"], returncode=0, stdout="Dark\n", stderr="")
        light_res = subprocess.CompletedProcess(args=["defaults"], returncode=1, stdout="", stderr="not found")
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(agent_team.sys, "platform", "darwin"),
            patch.object(agent_team.shutil, "which", return_value="/usr/bin/defaults"),
            patch("subprocess.run", return_value=dark_res),
        ):
            self.assertEqual(agent_team.detect_system_theme(), "dark")

        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(agent_team.sys, "platform", "darwin"),
            patch.object(agent_team.shutil, "which", return_value="/usr/bin/defaults"),
            patch("subprocess.run", return_value=light_res),
        ):
            self.assertEqual(agent_team.detect_system_theme(), "light")

    @patch("sys.stdout.isatty", return_value=True)
    def test_dark_style_preserves_original_cool_mascot_colors(self, _mock_isatty):
        with patch.dict(os.environ, {"AGT_THEME": "dark"}, clear=False):
            os.environ.pop("NO_COLOR", None)
            ps_grid = agent_team.render_7col_agent_ps_grid(
                active_roles={"architect": "1", "critic": "1"}, term_w=157
            )
            status_grid = agent_team.render_7col_agent_grid(term_w=157)

        self.assertIn("\033[38;2;228;255;255m", ps_grid)
        self.assertIn("\033[38;2;255;255;255m", ps_grid)
        self.assertIn("\033[1m\033[33m✦ ACTIVE ✦", ps_grid)
        self.assertIn("\033[38;2;136;192;208m", status_grid)
        self.assertIn("\033[38;2;196;167;231m", status_grid)

    @patch("sys.stdout.isatty", return_value=True)
    def test_light_style_ps_grid_uses_warm_pink_red_for_active_and_neutral_for_idle(self, _mock_isatty):
        active = {
            "architect": "1",
            "critic": "1",
            "orchestrator": "1",
            "implementer": "1",
            "searcher": "1",
        }
        with patch.dict(os.environ, {"AGT_THEME": "light"}, clear=False):
            os.environ.pop("NO_COLOR", None)
            ps_grid = agent_team.render_7col_agent_ps_grid(active_roles=active, term_w=157)

        self.assertNotIn("\033[38;2;228;255;255m", ps_grid)
        self.assertNotIn("\033[38;2;255;255;255m", ps_grid)

        lines = ps_grid.splitlines()
        crown_line = next(l for l in lines if "ACTIVE" in l)
        busy_line = next(l for l in lines if "BUSY" in l)
        role_line = next(l for l in lines if "[architect]" in l)

        for badge_line in (crown_line, busy_line):
            rgbs = _extract_rgbs(badge_line)
            self.assertTrue(rgbs, "Expected truecolor warm accent on ACTIVE/BUSY badges in light mode")
            for r, g, b in rgbs:
                self.assertTrue(r > g and r > b)
                self.assertLessEqual(_rgb_to_hsl_saturation(r, g, b), 0.58)
                self.assertGreaterEqual(_contrast_ratio((r, g, b), (237, 238, 242)), 4.0)
                self.assertGreaterEqual(_contrast_ratio((r, g, b), (255, 255, 255)), 4.5)

        role_rgbs = _extract_rgbs(role_line)
        self.assertEqual(len(role_rgbs), 5, "Only the 5 active roles should have warm RGB tags")
        for r, g, b in role_rgbs:
            self.assertTrue(r > g and r > b)
            self.assertGreaterEqual(r - g, 50)
            self.assertLessEqual(_rgb_to_hsl_saturation(r, g, b), 0.58)
            self.assertGreaterEqual(_contrast_ratio((r, g, b), (237, 238, 242)), 4.0)
            self.assertGreaterEqual(_contrast_ratio((r, g, b), (255, 255, 255)), 4.5)

        sprite_lines = [l for l in lines if "██" in l]
        all_sprite_rgbs = [rgb for l in sprite_lines for rgb in _extract_rgbs(l)]
        warm_blocks = [
            c for c in all_sprite_rgbs
            if c[0] > c[1] and c[0] > c[2] and c[0] - c[1] >= 50 and _rgb_to_hsl_saturation(*c) <= 0.58
        ]
        neutral_blocks = [
            c for c in all_sprite_rgbs
            if abs(c[0] - c[1]) <= 15 and abs(c[1] - c[2]) <= 15 and 2.0 <= _contrast_ratio(c, (237, 238, 242)) <= 3.5
        ]
        self.assertTrue(warm_blocks, "Expected warm pink/red sprite blocks for active mascots in light mode")
        self.assertTrue(neutral_blocks, "Expected neutral grey sprite blocks for idle mascots in light mode")

    @patch("sys.stdout.isatty", return_value=True)
    def test_light_style_status_grid_uses_warm_pink_red_mascots(self, _mock_isatty):
        with patch.dict(os.environ, {"AGT_PROVIDER": "agy", "AGT_THEME": "light"}, clear=True):
            grid = agent_team.render_7col_agent_grid(term_w=157)

        lines = grid.splitlines()
        role_line = next(l for l in lines if "[architect]" in l)
        role_rgbs = _extract_rgbs(role_line)
        self.assertEqual(len(role_rgbs), 8)
        for r, g, b in role_rgbs:
            self.assertTrue(r > g and r > b)
            self.assertGreaterEqual(r - g, 50)
            self.assertLessEqual(_rgb_to_hsl_saturation(r, g, b), 0.58)
            self.assertGreaterEqual(_contrast_ratio((r, g, b), (237, 238, 242)), 4.0)
            self.assertGreaterEqual(_contrast_ratio((r, g, b), (255, 255, 255)), 4.5)

        for c1, c2 in itertools.combinations(role_rgbs, 2):
            dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))
            self.assertGreaterEqual(dist, 18.0)

    @patch("sys.stdout.isatty", return_value=True)
    def test_light_style_ps_view_occupancy_uses_warm_role_labels_including_designer(self, _mock_isatty):
        with (
            patch.dict(os.environ, {"AGT_THEME": "light"}, clear=True),
            patch.object(agent_team, "get_live_os_procs", return_value=[]),
            patch.object(
                agent_team,
                "detect_live_agent_occupancy",
                return_value=({"lead-architect": "Planning", "designer": "Styling"}, []),
            ),
        ):
            view = agent_team.render_ps_view(Path("."))

        self.assertNotIn("\033[38;2;228;255;255m", view)
        arch_line = next(l for l in view.splitlines() if "[lead-architect]" in l)
        designer_line = next(l for l in view.splitlines() if "[designer]" in l)
        for line in (arch_line, designer_line):
            rgbs = _extract_rgbs(line)
            self.assertTrue(rgbs)
            for r, g, b in rgbs:
                self.assertTrue(r > g and r > b)
                self.assertGreaterEqual(r - g, 50)
                self.assertLessEqual(_rgb_to_hsl_saturation(r, g, b), 0.58)
                self.assertGreaterEqual(_contrast_ratio((r, g, b), (237, 238, 242)), 4.0)
                self.assertGreaterEqual(_contrast_ratio((r, g, b), (255, 255, 255)), 4.5)


if __name__ == "__main__":
    unittest.main()
