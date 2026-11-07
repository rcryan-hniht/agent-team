#!/usr/bin/env python3
"""
agent-team (agy-team): Multi-Agent Team & Skills Interactive Generator for ~/Projects
Tương thích chuẩn cấu trúc Workspace Agents của Orpheus / Act2Morse / Hephaestus:
  1. Antigravity (agy):
     - AGENTS.md, GEMINI.md
     - .agents/agents.json, .agents/README.md
     - .agents/agents/<role>/agent.md (YAML frontmatter: name, description, model, tools)
     - .agents/subagents/<role>.json (Payload cho define_subagent / invoke_subagent)
     - .agents/skills.json & .agents/skills/<skill_name>
     - .agents/rules/commit-restrictions.md (Tùy chọn)
  2. OpenAI Codex CLI (codex):
     - .agents/agents/<role>/agent.toml (model, model_reasoning_effort, developer_instructions)
     - .codex/config.toml ([agents] enabled = true, [agents.<role>] config_file = "../.agents/agents/<role>/agent.toml")
  3. Anthropic Claude Code (claude):
     - CLAUDE.md
     - .claude/agents/<role>.md
     - .claude/skills/<skill_name>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# ANSI Styling Helpers
# ---------------------------------------------------------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
RED = "\033[31m"


CURRENT_LANG = "en"


def tr(en_text: str, vi_text: str) -> str:
    return vi_text if CURRENT_LANG == "vi" else en_text


def c(text: str, color: str = "") -> str:
    if not sys.stdout.isatty():
        return text
    return f"{color}{text}{RESET}"


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _char_width(ch: str) -> int:
    if unicodedata.combining(ch):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def _visible_len(text: str) -> int:
    clean = ANSI_ESCAPE_RE.sub("", text)
    return sum(_char_width(ch) for ch in clean)


def _box_line(text: str, inner_width: int = 54) -> str:
    pad = max(0, inner_width - _visible_len(text))
    return f"{c('│', CYAN)}  {text}{' ' * pad}  {c('│', CYAN)}"


def rgb_fg(color: Tuple[int, int, int]) -> str:
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return ""
    return f"\033[38;2;{color[0]};{color[1]};{color[2]}m"


def _col(text: str, width: int, color_str: str = "") -> str:
    pad = max(0, width - _visible_len(text))
    colored = c(text, color_str) if color_str else text
    return colored + (" " * pad)


# ---------------------------------------------------------------------------
# 8-Role Chunky Pixel-Art Animals & Specifications
# Palettes: Nord, Rosé Pine, Blackmetal, Sequoia Monochrome (Cool Tones)
# ---------------------------------------------------------------------------
PIXEL_ART_ANIMALS = [
    (
        "lead-architect",
        (136, 192, 208),  # Nord 8 (Frost Ice Blue)
        "whale",
        "Lead Solution Architect & Planner",
        [
            ".#.#.",
            "..#..",
            ".###.",
            "#####",
            "#.#.#",
            "#...#",
        ],
        "gemini-4-argon-high",
        "gpt-6-astra (high)",
        "claude-opus-5-5-medium [Read-Only]",
        "agy:gemini-4-argon-high → agy:claude-opus-5-5-medium → agy:gemini-3.8-flash-high → codex:gpt-6-astra (high)",
    ),
    (
        "lead-critic",
        (196, 167, 231),  # Rosé Pine Iris (Lavender)
        "orca",
        "Lead Technical Critic & Challenger",
        [
            "..#..",
            ".###.",
            "#.#.#",
            "#####",
            ".###.",
            "#...#",
        ],
        "gemini-3.1-pro-high",
        "gpt-6.1-sol (xhigh)",
        "claude-opus-5-5-medium [Read-Only]",
        "agy:gemini-3.1-pro-high → agy:claude-opus-5-5-medium → agy:gemini-3.8-flash-high → codex:gpt-6.1-sol (xhigh)",
    ),
    (
        "orchestrator",
        (143, 188, 187),  # Nord 7 (Glacial Teal)
        "octopus",
        "Lead Execution Orchestrator",
        [
            ".###.",
            "#####",
            "#.#.#",
            "#####",
            "#.#.#",
            "#.#.#",
        ],
        "gemini-4-argon-high",
        "gpt-6-astra (high)",
        "claude-opus-5-5-medium [Read-Only]",
        "agy:gemini-4-argon-high → agy:claude-opus-5-5-medium → agy:gemini-3.8-flash-high → codex:gpt-6.1-sol (xhigh)",
    ),
    (
        "reviewer",
        (163, 190, 140),  # Nord 14 (Frosted Sage)
        "shark",
        "Independent Code Quality & Security Reviewer",
        [
            "..#..",
            ".###.",
            "#.#.#",
            "#####",
            "..#..",
            "#...#",
        ],
        "gemini-3.1-pro-high",
        "gpt-6.1-sol (xhigh)",
        "sonnet [Read-Only]",
        "agy:gemini-3.1-pro-high → agy:claude-opus-5-5-medium → agy:gemini-3.8-flash-high → codex:gpt-6.1-sol (xhigh)",
    ),
    (
        "designer",
        (246, 193, 119),  # Rosé Pine Gold (Warm Accent)
        "southern rockhopper penguin",
        "UI/UX & Anti-Slop Visual Designer",
        [
            "#...#",
            ".###.",
            "##.##",
            ".###.",
            "#####",
            ".#.#.",
        ],
        "gemini-3.8-flash-high",
        "gpt-6-sol (xhigh)",
        "sonnet [Write]",
        "agy:gemini-3.8-flash-high → agy:gemini-3.1-pro-high → claude:sonnet → codex:gpt-6-sol (xhigh)",
    ),
    (
        "implementer",
        (129, 161, 193),  # Nord 9 (Glacier Arctic Blue)
        "hammerhead shark",
        "Senior Feature & TDD Implementer",
        [
            "#####",
            "#...#",
            ".###.",
            "#####",
            "..#..",
            "#...#",
        ],
        "gemini-3.8-flash-high",
        "gpt-6-sol (xhigh)",
        "sonnet [Write]",
        "agy:gemini-3.8-flash-high → agy:gemini-3.1-pro-high → claude:sonnet → codex:gpt-6-sol (xhigh)",
    ),
    (
        "searcher",
        (144, 140, 170),  # Rosé Pine Subtle / Blackmetal Frosted Lilac
        "swordfish",
        "Primary Documentation & Codebase Scout",
        [
            "..#..",
            "..#..",
            ".###.",
            "#####",
            "..#..",
            "#...#",
        ],
        "gemini-3.8-flash-medium",
        "gpt-6-luna (medium)",
        "haiku [Read-Only]",
        "agy:gemini-3.8-flash-medium → agy:gemini-3.8-flash-high → claude:haiku → codex:gpt-6-luna (medium)",
    ),
    (
        "committer",
        (94, 129, 172),  # Nord 10 (Deep Steel Blue)
        "starfish",
        "Conventional Git Committer",
        [
            "..#..",
            "..#..",
            "#####",
            ".###.",
            ".#.#.",
            "#...#",
        ],
        "gemini-3.7-flash",
        "gpt-6-luna (low)",
        "haiku [Read-Only]",
        "agy:gemini-3.7-flash → agy:gemini-3.8-flash-medium → claude:haiku → codex:gpt-6-luna (low)",
    ),
]

ROLE_COLORS = {r[0]: r[1] for r in PIXEL_ART_ANIMALS}

# Soothing Rosé Pine Dawn / Warm Rosewood & Blush palette for Light system theme (WCAG AA, S <= 57%)
LIGHT_ROLE_COLORS: Dict[str, Tuple[int, int, int]] = {
    "lead-architect": (178, 54, 76),   # Antique Rosewood Red (#B2364C)
    "lead-critic": (168, 62, 104),     # Muted Berry Wine (#A83E68)
    "orchestrator": (182, 70, 56),     # Warm Terracotta Brick (#B64638)
    "reviewer": (152, 56, 92),         # Deep Plum Wine (#98385C)
    "designer": (188, 76, 110),        # Soft Blush Pink (#BC4C6E)
    "implementer": (180, 84, 68),      # Desert Coral (#B45444)
    "searcher": (158, 72, 122),        # Smoky Mauve Orchid (#9E487A)
    "committer": (164, 48, 56),        # Vintage Carmine Brick (#A43038)
}
LIGHT_ACTIVE_BADGE_RGB: Tuple[int, int, int] = (180, 50, 70)    # Rosewood Garnet (#B43246)
LIGHT_IDLE_SPRITE_RGB: Tuple[int, int, int] = (148, 144, 156)   # Muted Lavender Grey (#94909C)


def detect_system_theme() -> str:
    """Auto-detect system/terminal appearance ('light' or 'dark'); defaults to 'dark'."""
    env_theme = os.environ.get("AGT_THEME", "").strip().lower()
    if env_theme in ("light", "dark"):
        return env_theme

    colorfgbg = os.environ.get("COLORFGBG", "").strip()
    if ";" in colorfgbg:
        bg_part = colorfgbg.rsplit(";", 1)[-1].strip()
        if bg_part.isdigit():
            bg_idx = int(bg_part)
            if bg_idx in (7, 15):
                return "light"
            if 0 <= bg_idx <= 8:
                return "dark"

    if sys.platform == "darwin" and shutil.which("defaults"):
        try:
            res = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
                timeout=0.4,
            )
            return "dark" if res.returncode == 0 and "dark" in res.stdout.lower() else "light"
        except Exception:
            return "dark"

    if sys.platform.startswith("linux"):
        try:
            dms_session = Path.home() / ".local" / "state" / "DankMaterialShell" / "session.json"
            if dms_session.exists():
                dms_data = json.loads(dms_session.read_text(encoding="utf-8"))
                if isinstance(dms_data.get("isLightMode"), bool):
                    return "light" if dms_data["isLightMode"] else "dark"
        except Exception:
            pass

        if (
            os.environ.get("WAYLAND_DISPLAY")
            or os.environ.get("DISPLAY")
            or os.environ.get("DBUS_SESSION_BUS_ADDRESS")
        ) and shutil.which("gsettings"):
            try:
                res = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                    capture_output=True,
                    text=True,
                    timeout=0.4,
                )
                if res.returncode == 0:
                    scheme = res.stdout.strip().strip("'").strip('"').lower()
                    if scheme == "prefer-dark":
                        return "dark"
                    if scheme in ("prefer-light", "default"):
                        return "light"
            except Exception:
                pass

    return "dark"


def _mascot_role_rgb(role_id: str, theme: str, active_boost: bool = False) -> Tuple[int, int, int]:
    if theme == "light":
        return LIGHT_ROLE_COLORS.get(role_id, LIGHT_ACTIVE_BADGE_RGB)
    base = ROLE_COLORS.get(role_id, (255, 255, 255))
    if active_boost:
        return (
            min(255, int(base[0] * 1.35 + 45)),
            min(255, int(base[1] * 1.35 + 45)),
            min(255, int(base[2] * 1.35 + 45)),
        )
    return base


ROLE_ANIMALS = {r[0]: r[2] for r in PIXEL_ART_ANIMALS}
ROLE_ANIMALS_VI = {
    "lead-architect": "cá voi",
    "lead-critic": "cá voi sát thủ",
    "orchestrator": "bạch tuộc",
    "reviewer": "cá mập",
    "designer": "chim cánh cụt rockhopper phương nam",
    "implementer": "cá mập đầu búa",
    "searcher": "cá kiếm",
    "committer": "sao biển",
}

ROLE_DESCRIPTIONS_EN = {
    "lead-architect": "Lead Solution Architect & Planner",
    "lead-critic": "Lead Technical Critic & Challenger",
    "orchestrator": "Execution Orchestration & Worker Dispatcher",
    "reviewer": "Independent Code Quality & Security Reviewer",
    "designer": "UI/UX & Anti-Slop Visual Designer",
    "implementer": "Senior Feature & TDD Implementer",
    "searcher": "Primary Documentation & Codebase Scout",
    "committer": "Conventional Git Committer",
}

ROLE_DESCRIPTIONS_VI = {
    "lead-architect": "Kiến trúc sư trưởng & Hoạch định giải pháp",
    "lead-critic": "Phản biện trưởng & Thẩm định rủi ro kỹ thuật",
    "orchestrator": "Tổng điều phối viên thực thi",
    "reviewer": "Kiểm định viên chất lượng & Bảo mật độc lập",
    "designer": "Kỹ sư thiết kế UI/UX & Bản sắc thị giác Anti-Slop",
    "implementer": "Kỹ sư thực thi tính năng & TDD",
    "searcher": "Trinh sát mã nguồn & Tra cứu tài liệu",
    "committer": "Chuyên viên đóng gói Git Commit",
}

ROLE_TASK_DEFAULT_EN = {
    "lead-architect": "Drafting architecture RFC & task breakdown",
    "lead-critic": "Reviewing technical risks & stress-testing design",
    "orchestrator": "Orchestrating subagents & execution pipeline",
    "reviewer": "Reviewing code correctness & security standards",
    "designer": "Designing anti-slop UI tokens & styling components",
    "implementer": "Implementing minimal code & unit tests (TDD)",
    "searcher": "Scouting codebase & researching documentation",
    "committer": "Packaging conventional git commits",
}

ROLE_TASK_DEFAULT_VI = {
    "lead-architect": "Đang lập đề xuất kiến trúc & phân rã nhiệm vụ",
    "lead-critic": "Đang phản biện rủi ro kỹ thuật & stress-test thiết kế",
    "orchestrator": "Đang điều phối các subagent & kế hoạch thực thi",
    "reviewer": "Đang kiểm định chất lượng code & bảo mật",
    "designer": "Đang thiết kế token giao diện & tạo mẫu UI anti-slop",
    "implementer": "Đang viết code & kiểm thử đơn vị (TDD)",
    "searcher": "Đang trinh sát mã nguồn & tra cứu tài liệu",
    "committer": "Đang đóng gói git commit chuẩn Conventional Commits",
}


def format_active_role_desc(r_id: str, info: Any, lang: str = "en") -> str:
    """Format the active role description cleanly according to the selected language."""
    if isinstance(info, dict):
        prompt = str(info.get("prompt", "")).strip().strip('"').strip("'")
        is_heuristic = info.get("is_heuristic", False)
        is_manual = info.get("is_manual", False)

        if is_heuristic or is_manual:
            return prompt

        if lang == "vi":
            role_desc = ROLE_DESCRIPTIONS_VI.get(r_id, info.get("role_raw") or "Chuyên viên")
            if _is_vi_text(prompt) and prompt:
                clean_p = prompt
                for prefix in (f"Bạn là `{r_id}`", f"Bạn là {r_id}", "Bạn là"):
                    if clean_p.startswith(prefix):
                        if "Nhiệm vụ:" in clean_p:
                            clean_p = clean_p.split("Nhiệm vụ:", 1)[1].strip()
                        elif ":" in clean_p:
                            clean_p = clean_p.split(":", 1)[1].strip()
                        break
                clean_p = clean_p[:70].strip().strip('"').strip("'")
                return f"{role_desc} — {clean_p}…" if len(clean_p) >= 70 else f"{role_desc} — {clean_p}"
            else:
                task_desc = ROLE_TASK_DEFAULT_VI.get(r_id, "Đang xử lý nhiệm vụ")
                return f"{role_desc} — {task_desc}"
        else:
            role_desc = ROLE_DESCRIPTIONS_EN.get(r_id, "Specialist")
            if not _is_vi_text(prompt) and prompt:
                clean_p = prompt
                for prefix in (f"You are `{r_id}`", f"You are {r_id}", "You are"):
                    if clean_p.startswith(prefix):
                        if "Mission:" in clean_p:
                            clean_p = clean_p.split("Mission:", 1)[1].strip()
                        elif ":" in clean_p:
                            clean_p = clean_p.split(":", 1)[1].strip()
                        break
                clean_p = clean_p[:70].strip().strip('"').strip("'")
                return f"{role_desc} — {clean_p}…" if len(clean_p) >= 70 else f"{role_desc} — {clean_p}"
            else:
                task_desc = ROLE_TASK_DEFAULT_EN.get(r_id, "Executing assigned task")
                return f"{role_desc} — {task_desc}"

    if isinstance(info, str):
        raw_str = info.strip().strip('"').strip("'")
        if lang == "en" and _is_vi_text(raw_str):
            role_desc = ROLE_DESCRIPTIONS_EN.get(r_id, "Specialist")
            task_desc = ROLE_TASK_DEFAULT_EN.get(r_id, "Executing assigned task")
            return f"{role_desc} — {task_desc}"
        elif lang == "vi" and not _is_vi_text(raw_str):
            role_desc = ROLE_DESCRIPTIONS_VI.get(r_id, "Chuyên viên")
            task_desc = ROLE_TASK_DEFAULT_VI.get(r_id, "Đang xử lý nhiệm vụ")
            return f"{role_desc} — {task_desc}"
        return raw_str

    role_desc = ROLE_DESCRIPTIONS_VI.get(r_id, "Chuyên viên") if lang == "vi" else ROLE_DESCRIPTIONS_EN.get(r_id, "Specialist")
    task_desc = ROLE_TASK_DEFAULT_VI.get(r_id, "Đang xử lý nhiệm vụ") if lang == "vi" else ROLE_TASK_DEFAULT_EN.get(r_id, "Executing assigned task")
    return f"{role_desc} — {task_desc}"


def _classify_proc_provider(comm: str, cmdline: str = "") -> Optional[str]:
    if "app-server" in cmdline or "--managed-daemon" in cmdline:
        return None
    return {
        "agy": "agy",
        "gemini": "agy",
        "antigravity": "agy",
        "codex": "codex",
        "codex-cli": "codex",
        "claude": "claude",
        "claude-code": "claude",
    }.get(comm.lower())


def detect_active_providers(project_path: Optional[Path] = None) -> Set[str]:
    """Return active providers, scoped to project_path when it is supplied."""
    providers = {"agy", "codex", "claude"}
    override = os.environ.get("AGT_PROVIDER") or os.environ.get("AGT_ACTIVE_PROVIDER")
    if override:
        selected = {p.strip().lower() for p in override.split(",")} & providers
        if selected:
            return selected

    env_providers = set()
    if any(k in os.environ for k in ("ANTIGRAVITY_AGENT", "ANTIGRAVITY_CONVERSATION_ID", "ANTIGRAVITY_LS_ADDRESS", "ANTIGRAVITY_APP_DATA_DIR")):
        env_providers.add("agy")
    if any(k in os.environ for k in ("CODEX_ENV", "CODEX_SESSION", "CODEX_SHELL")):
        env_providers.add("codex")
    if any(k in os.environ for k in ("CLAUDE_CODE_ENTRYPOINT", "CLAUDE_AGENT", "CLAUDE_SHELL")):
        env_providers.add("claude")

    if project_path is None and env_providers:
        return env_providers

    active = set()
    try:
        resolved_proj = project_path.resolve() if project_path is not None else None
        if resolved_proj is not None and Path.cwd().resolve() == resolved_proj:
            active.update(env_providers)

        cur_pid = os.getpid()
        for _ in range(6):
            status_file = Path(f"/proc/{cur_pid}/status")
            if not status_file.exists():
                break
            ppid = None
            for line in status_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith("PPid:"):
                    ppid = int(line.split()[1])
                    break
            if not ppid or ppid <= 1:
                break

            proc_path = Path(f"/proc/{ppid}")
            if resolved_proj is None or (proc_path / "cwd").resolve() == resolved_proj:
                comm_file = proc_path / "comm"
                cmdline_file = proc_path / "cmdline"
                comm = comm_file.read_text(encoding="utf-8", errors="ignore").strip() if comm_file.exists() else ""
                cmdline = cmdline_file.read_bytes().replace(b"\x00", b" ").decode("utf-8", errors="ignore") if cmdline_file.exists() else ""
                provider = _classify_proc_provider(comm, cmdline)
                if provider:
                    active.add(provider)
            cur_pid = ppid
    except Exception:
        pass

    if project_path is None:
        return active or {"agy"}

    try:
        for proc in get_live_os_procs(project_path.resolve()):
            if proc.get("in_project"):
                provider = _classify_proc_provider(proc.get("comm", ""), proc.get("cmdline", ""))
                if provider:
                    active.add(provider)
    except Exception:
        pass

    if active:
        return active

    try:
        cfg = project_path / ".agents" / "team-config.json"
        if cfg.exists():
            data = json.loads(cfg.read_text(encoding="utf-8"))
            harnesses = data.get("harnesses", [])
            if harnesses and harnesses[0] in providers:
                return {harnesses[0]}
    except Exception:
        pass
    return {"agy"}


def detect_active_provider(project_path: Optional[Path] = None) -> str:
    active = detect_active_providers(project_path)
    return next((p for p in ("agy", "codex", "claude") if p in active), "")


MASCOT_LABELS_EN = {
    "lead-architect": ("whale", ""),
    "lead-critic": ("orca", ""),
    "orchestrator": ("octopus", ""),
    "reviewer": ("shark", ""),
    "designer": ("rockhopper", "penguin"),
    "implementer": ("hammerhead", "shark"),
    "searcher": ("swordfish", ""),
    "committer": ("starfish", ""),
}

MASCOT_LABELS_VI = {
    "lead-architect": ("cá voi", ""),
    "lead-critic": ("cá voi", "sát thủ"),
    "orchestrator": ("bạch tuộc", ""),
    "reviewer": ("cá mập", ""),
    "designer": ("cánh cụt", "rockhopper"),
    "implementer": ("cá mập", "đầu búa"),
    "searcher": ("cá kiếm", ""),
    "committer": ("sao biển", ""),
}


def render_7col_agent_grid(
    agents_data: Optional[List[Dict]] = None,
    term_w: Optional[int] = None,
    project_path: Optional[Path] = None,
    theme: Optional[str] = None,
) -> str:
    """Render 8 columns (art, animal name, roles, model, reasoning effects) with 4 rows (agy, codex, claude, fallback)."""
    resolved_theme = theme if theme in ("light", "dark") else detect_system_theme()

    if term_w is None:
        term_w = shutil.get_terminal_size((115, 24)).columns
    num_cols = len(PIXEL_ART_ANIMALS)
    hdr_w = 10
    avail_w = term_w - hdr_w
    cell_w = max(11, min(18, avail_w // num_cols))
    total_w = hdr_w + cell_w * num_cols
    margin = max(0, (term_w - total_w) // 2)
    m = " " * margin

    if cell_w >= 18:
        agy_specs = ["argon (high)", "pro-3.1 (high)", "argon (high)", "pro-3.1 (high)", "flash-3.8 (high)", "flash-3.8 (high)", "flash-3.8 (med)", "flash-3.7 (low)"]
        codex_specs = ["astra (high)", "sol-6.1 (xhigh)", "astra (high)", "sol-6.1 (xhigh)", "sol-6 (xhigh)", "sol-6 (xhigh)", "luna (medium)", "luna (low)"]
        claude_specs = ["opus-5.5 [RO]", "opus-5.5 [RO]", "opus-5.5 [RO]", "sonnet [RO]", "sonnet [Write]", "sonnet [Write]", "haiku [RO]", "haiku [RO]"]
        fb_specs = ["→opus→flash→astra", "→opus→flash→sol", "→opus→flash→sol", "→opus→flash→sol", "→pro→sonnet→sol", "→pro→sonnet→sol", "→flash→haiku→luna", "→fl-m→haiku→luna"]
    elif cell_w >= 15:
        agy_specs = ["argon (high)", "pro-3.1 (h)", "argon (high)", "pro-3.1 (h)", "flash-3.8 (h)", "flash-3.8 (h)", "flash-3.8 (m)", "flash-3.7 (l)"]
        codex_specs = ["astra (high)", "sol-6.1 (xh)", "astra (high)", "sol-6.1 (xh)", "sol-6 (xh)", "sol-6 (xh)", "luna (med)", "luna (low)"]
        claude_specs = ["opus-5.5 [RO]", "opus-5.5 [RO]", "opus-5.5 [RO]", "sonnet [RO]", "sonnet [W]", "sonnet [W]", "haiku [RO]", "haiku [RO]"]
        fb_specs = ["→opus→astra", "→opus→sol", "→opus→sol", "→opus→sol", "→pro→sonnet", "→pro→sonnet", "→haiku→luna", "→haiku→luna"]
    elif cell_w >= 13:
        agy_specs = ["argon (h)", "pro-3.1(h)", "argon (h)", "pro-3.1(h)", "fl-3.8 (h)", "fl-3.8 (h)", "fl-3.8 (m)", "fl-3.7 (l)"]
        codex_specs = ["astra (h)", "sol-6.1(xh)", "astra (h)", "sol-6.1(xh)", "sol-6 (xh)", "sol-6 (xh)", "luna (med)", "luna (low)"]
        claude_specs = ["opus-5.5[RO]", "opus-5.5[RO]", "opus-5.5[RO]", "sonnet[RO]", "sonnet [W]", "sonnet [W]", "haiku [RO]", "haiku [RO]"]
        fb_specs = ["→opus→astra", "→opus→sol", "→opus→sol", "→opus→sol", "→pro→sol", "→pro→sol", "→haiku→luna", "→haiku→luna"]
    else:
        agy_specs = ["argon(h)", "pro(h)", "argon(h)", "pro(h)", "fl-3.8(h)", "fl-3.8(h)", "fl-3.8(m)", "fl-3.7(l)"]
        codex_specs = ["astra(h)", "sol(xh)", "astra(h)", "sol(xh)", "sol(xh)", "sol(xh)", "luna(m)", "luna(l)"]
        claude_specs = ["opus[RO]", "opus[RO]", "opus[RO]", "son[RO]", "son[W]", "son[W]", "haiku[RO]", "haiku[RO]"]
        fb_specs = ["→opus→ast", "→opus→sol", "→opus→sol", "→opus→sol", "→pro→sol", "→pro→sol", "→hai→lu", "→hai→lu"]

    lines = []
    lines.append("")
    # 6 rows of sprite (no border box)
    for r in range(6):
        row = m + " " * hdr_w
        for k in range(num_cols):
            role_id = PIXEL_ART_ANIMALS[k][0]
            grid = PIXEL_ART_ANIMALS[k][4]
            color = _mascot_role_rgb(role_id, resolved_theme)
            s = "".join((rgb_fg(color) + "██" + RESET) if ch == "#" else "  " for ch in grid[r])
            pad = max(0, cell_w - 10)
            row += " " * (pad // 2) + s + " " * (pad - pad // 2)
        lines.append(row)

    # Mascot Name 2 Lines
    mascot_labels = MASCOT_LABELS_VI if CURRENT_LANG == "vi" else MASCOT_LABELS_EN
    for line_idx in (0, 1):
        row = m + " " * hdr_w
        for k in range(num_cols):
            role_id = PIXEL_ART_ANIMALS[k][0]
            color = _mascot_role_rgb(role_id, resolved_theme)
            w = mascot_labels.get(role_id, ("", ""))[line_idx]
            vis_w_len = _visible_len(w)
            pad = max(0, cell_w - vis_w_len)
            colored_w = f"{rgb_fg(color)}{BOLD}{w}{RESET}" if sys.stdout.isatty() else w
            row += " " * (pad // 2) + colored_w + " " * (pad - pad // 2)
        lines.append(row)

    # Roles
    row = m + " " * hdr_w
    if CURRENT_LANG == "vi":
        roles_mid = ["[kiến trúc]", "[phản biện]", "[điều phối]", "[kiểm định]", "[thiết kế]", "[thực thi]", "[trinh sát]", "[đóng gói]"]
        roles_short = ["[k.trúc]", "[p.biện]", "[đ.phối]", "[k.định]", "[t.kế]", "[t.thi]", "[t.sát]", "[đ.gói]"]
    else:
        roles_mid = ["[architect]", "[critic]", "[orchestrator]", "[reviewer]", "[designer]", "[implementer]", "[searcher]", "[committer]"]
        roles_short = ["[arch]", "[critic]", "[orch]", "[reviewer]", "[design]", "[imp]", "[search]", "[commit]"]
    for k in range(num_cols):
        role_id = PIXEL_ART_ANIMALS[k][0]
        color = _mascot_role_rgb(role_id, resolved_theme)
        tag = roles_mid[k] if cell_w >= 14 else roles_short[k]
        vis_tag_len = _visible_len(tag)
        pad = max(0, cell_w - vis_tag_len)
        colored_tag = f"{rgb_fg(color)}{BOLD}{tag}{RESET}" if sys.stdout.isatty() else tag
        row += " " * (pad // 2) + colored_tag + " " * (pad - pad // 2)
    lines.append(row)

    # Divider
    lines.append(m + DIM + "─" * total_w + RESET)

    # 4 rows: agy, codex, claude, fallback with dynamic active provider accent
    active_ps = detect_active_providers(project_path)
    agy_c = YELLOW if "agy" in active_ps else CYAN
    codex_c = YELLOW if "codex" in active_ps else CYAN
    claude_c = YELLOW if "claude" in active_ps else CYAN

    row_defs = [
        ("agy:", agy_c, agy_specs, "agy" in active_ps),
        ("codex:", codex_c, codex_specs, "codex" in active_ps),
        ("claude:", claude_c, claude_specs, "claude" in active_ps),
        ("fallback:", DIM, fb_specs, False),
    ]
    for lbl, col_c, vals, is_active_row in row_defs:
        row = m + BOLD + col_c + lbl.ljust(hdr_w) + RESET
        write_color = GREEN if is_active_row else CYAN
        for k in range(num_cols):
            v = vals[k]
            if len(v) > cell_w:
                v = v[:cell_w - 1] + "…"
            pad = max(0, cell_w - len(v))
            disp_v = v
            if sys.stdout.isatty():
                if "[Write]" in disp_v:
                    disp_v = disp_v.replace("[Write]", f"{write_color}[Write]{RESET}{col_c}")
                elif "[W]" in disp_v:
                    disp_v = disp_v.replace("[W]", f"{write_color}[W]{RESET}{col_c}")
                elif "[RO]" in disp_v:
                    disp_v = disp_v.replace("[RO]", f"{DIM}[RO]{RESET}{col_c}")
                disp_v = f"{col_c}{disp_v}{RESET}"
            row += " " * (pad // 2) + disp_v + " " * (pad - pad // 2)
        lines.append(row)

    lines.append(m + DIM + "─" * total_w + RESET)
    lines.append("")
    return "\n".join(lines)


render_agent_grid = render_7col_agent_grid


# Mascot Emojis for status and ps monitor
MASCOT_EMOJIS = {
    "lead-architect": "🐋",
    "lead-critic": "🐋",
    "orchestrator": "🐙",
    "reviewer": "🦈",
    "designer": "🐧",
    "implementer": "🦈",
    "searcher": "🐟",
    "committer": "⭐",
}

ROLE_ALIASES = {
    "architect": "lead-architect",
    "lead-architect": "lead-architect",
    "arch": "lead-architect",
    "owl": "lead-architect",
    "whale": "lead-architect",
    "cá voi": "lead-architect",
    "critic": "lead-critic",
    "lead-critic": "lead-critic",
    "cat": "lead-critic",
    "orca": "lead-critic",
    "killer whale": "lead-critic",
    "cá voi sát thủ": "lead-critic",
    "orchestrator": "orchestrator",
    "orch": "orchestrator",
    "octopus": "orchestrator",
    "bạch tuộc": "orchestrator",
    "reviewer": "reviewer",
    "rev": "reviewer",
    "frog": "reviewer",
    "shark": "reviewer",
    "cá mập": "reviewer",
    "designer": "designer",
    "ui-designer": "designer",
    "ui": "designer",
    "design": "designer",
    "rockhopper": "designer",
    "penguin": "designer",
    "southern rockhopper penguin": "designer",
    "cánh cụt": "designer",
    "chim cánh cụt": "designer",
    "implementer": "implementer",
    "imp": "implementer",
    "hawk": "implementer",
    "falcon": "implementer",
    "chim ưng": "implementer",
    "rabbit": "implementer",
    "hammerhead": "implementer",
    "hammerhead shark": "implementer",
    "cá mập đầu búa": "implementer",
    "searcher": "searcher",
    "search": "searcher",
    "swordfish": "searcher",
    "marlin": "searcher",
    "cá kiếm": "searcher",
    "bat": "searcher",
    "committer": "committer",
    "commit": "committer",
    "starfish": "starfish",
    "sao biển": "committer",
}


def render_7col_agent_ps_grid(
    active_roles: Optional[Dict[str, str]] = None,
    term_w: Optional[int] = None,
    theme: Optional[str] = None,
) -> str:
    """
    Render 8 columns of mascot pixel art with dynamic glowing effect for active roles.
    - Active roles: Radiant boosted RGB colors (warm pink/red in light mode), bold role tag, '● working' badge.
    - Idle roles: Dimmed/neutral palette, dim role tag, '○ idle' badge.
    """
    resolved_theme = theme if theme in ("light", "dark") else detect_system_theme()
    is_light = resolved_theme == "light"
    active_badge_c = (rgb_fg(LIGHT_ACTIVE_BADGE_RGB) or YELLOW) if is_light else YELLOW

    if active_roles is None:
        active_roles = {}
    normalized_active: Dict[str, str] = {}
    for k, v in active_roles.items():
        clean_k = k.strip().lower()
        canonical = ROLE_ALIASES.get(clean_k, clean_k)
        normalized_active[canonical] = v

    if term_w is None:
        term_w = shutil.get_terminal_size((115, 24)).columns
    num_cols = len(PIXEL_ART_ANIMALS)
    hdr_w = 4
    avail_w = term_w - hdr_w
    cell_w = max(11, min(18, avail_w // num_cols))
    total_w = hdr_w + cell_w * num_cols
    margin = max(0, (term_w - total_w) // 2)
    m = " " * margin

    lines = []
    lines.append("")

    # 6 rows of sprite
    for r in range(6):
        row = m + " " * hdr_w
        for k in range(num_cols):
            role_id = PIXEL_ART_ANIMALS[k][0]
            color = PIXEL_ART_ANIMALS[k][1]
            grid = PIXEL_ART_ANIMALS[k][4]
            is_active = role_id in normalized_active
            if is_active:
                boost_c = _mascot_role_rgb(role_id, resolved_theme, active_boost=True)
                if sys.stdout.isatty():
                    s = "".join((f"{BOLD}{rgb_fg(boost_c)}██{RESET}") if ch == "#" else "  " for ch in grid[r])
                else:
                    s = "".join("██" if ch == "#" else "  " for ch in grid[r])
            else:
                if sys.stdout.isatty():
                    if is_light:
                        s = "".join((f"{rgb_fg(LIGHT_IDLE_SPRITE_RGB)}██{RESET}") if ch == "#" else "  " for ch in grid[r])
                    else:
                        dim_c = (
                            max(20, int(color[0] * 0.42)),
                            max(20, int(color[1] * 0.42)),
                            max(20, int(color[2] * 0.42)),
                        )
                        s = "".join((f"{DIM}{rgb_fg(dim_c)}██{RESET}") if ch == "#" else "  " for ch in grid[r])
                else:
                    s = "".join("░░" if ch == "#" else "  " for ch in grid[r])
            pad = max(0, cell_w - 10)
            row += " " * (pad // 2) + s + " " * (pad - pad // 2)
        lines.append(row)

    # Mascot Name 2 Lines
    mascot_labels = MASCOT_LABELS_VI if CURRENT_LANG == "vi" else MASCOT_LABELS_EN
    for line_idx in (0, 1):
        row = m + " " * hdr_w
        for k in range(num_cols):
            role_id = PIXEL_ART_ANIMALS[k][0]
            w = mascot_labels.get(role_id, ("", ""))[line_idx]
            is_active = role_id in normalized_active
            vis_w_len = _visible_len(w)
            pad = max(0, cell_w - vis_w_len)
            if is_active:
                boost_c = _mascot_role_rgb(role_id, resolved_theme, active_boost=True)
                colored_w = f"{BOLD}{rgb_fg(boost_c)}{w}{RESET}" if sys.stdout.isatty() else w
            else:
                colored_w = f"{DIM}{w}{RESET}" if sys.stdout.isatty() else w
            row += " " * (pad // 2) + colored_w + " " * (pad - pad // 2)
        lines.append(row)

    # Roles
    if CURRENT_LANG == "vi":
        roles_mid = ["[kiến trúc]", "[phản biện]", "[điều phối]", "[kiểm định]", "[thiết kế]", "[thực thi]", "[trinh sát]", "[đóng gói]"]
        roles_short = ["[k.trúc]", "[p.biện]", "[đ.phối]", "[k.định]", "[t.kế]", "[t.thi]", "[t.sát]", "[đ.gói]"]
    else:
        roles_mid = ["[architect]", "[critic]", "[orchestrator]", "[reviewer]", "[designer]", "[implementer]", "[searcher]", "[committer]"]
        roles_short = ["[arch]", "[critic]", "[orch]", "[reviewer]", "[design]", "[imp]", "[search]", "[commit]"]
    row = m + " " * hdr_w
    for k in range(num_cols):
        role_id = PIXEL_ART_ANIMALS[k][0]
        is_active = role_id in normalized_active
        tag = roles_mid[k] if cell_w >= 14 else roles_short[k]
        vis_tag_len = _visible_len(tag)
        pad = max(0, cell_w - vis_tag_len)
        if is_active:
            boost_c = _mascot_role_rgb(role_id, resolved_theme, active_boost=True)
            colored_tag = f"{BOLD}{rgb_fg(boost_c)}{tag}{RESET}" if sys.stdout.isatty() else tag
        else:
            colored_tag = f"{DIM}{tag}{RESET}" if sys.stdout.isatty() else tag
        row += " " * (pad // 2) + colored_tag + " " * (pad - pad // 2)
    lines.append(row)

    # State row (working vs idle)
    row = m + " " * hdr_w
    for k in range(num_cols):
        role_id = PIXEL_ART_ANIMALS[k][0]
        is_active = role_id in normalized_active
        if is_active:
            st = "● working"
            colored_st = f"{BOLD}{active_badge_c}{st}{RESET}" if sys.stdout.isatty() else st
        else:
            st = "○ idle"
            colored_st = f"{DIM}{st}{RESET}" if sys.stdout.isatty() else st
        vis_len = _visible_len(st)
        pad = max(0, cell_w - vis_len)
        row += " " * (pad // 2) + colored_st + " " * (pad - pad // 2)
    lines.append(row)

    lines.append(m + DIM + "─" * total_w + RESET)
    return "\n".join(lines)


render_agent_ps_grid = render_7col_agent_ps_grid


# Backward compatibility alias
render_pixel_art_banner = render_7col_agent_grid


def banner() -> None:
    box_w = 58
    ascii_art = [
        c("   █████╗  ██████╗ ████████╗", BOLD + CYAN),
        c("  ██╔══██╗██╔════╝ ╚══██╔══╝", BOLD + CYAN),
        c("  ███████║██║  ███╗   ██║   ", BOLD + CYAN),
        c("  ██╔══██║██║   ██║   ██║   ", BOLD + GREEN),
        c("  ██║  ██║╚██████╔╝   ██║   ", BOLD + GREEN),
        c("  ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ", DIM + GREEN),
    ]

    if CURRENT_LANG == "vi":
        header_title = " ✦ AGENT-TEAM "
        line_1 = f"{c('▸ NỀN TẢNG', BOLD + YELLOW)} : Antigravity • OpenAI Codex • Claude Code"
        line_2 = f"{c('▸ PHA 1   ', BOLD + GREEN)} : Cặp Lead Phản Biện 2 Vòng (Argon ⮂ Pro 3.1)"
        line_3 = f"{c('▸ PHA 2   ', BOLD + GREEN)} : Orchestrator Điều Phối [Search/Imp/Design/Rev/Git]"
        line_4 = f"{c('▸ CƠ CHẾ  ', BOLD + YELLOW)} : Đồng Thuận Thiết Kế ➔ Thực Thi TDD Phân Cấp"
        footer_tag = " ◈ .agents   ◈ .codex   ◈ .claude   ◈ 150+ skills "
    else:
        header_title = " ✦ AGENT-TEAM "
        line_1 = f"{c('▸ HARNESS', BOLD + YELLOW)} : Antigravity • OpenAI Codex • Claude Code"
        line_2 = f"{c('▸ PHASE 1', BOLD + GREEN)} : Lead Architect ⮂ Lead Critic (2-Rnd Debate)"
        line_3 = f"{c('▸ PHASE 2', BOLD + GREEN)} : Orchestrator → [Search/Imp/Design/Rev/Commit]"
        line_4 = f"{c('▸ PATTERN', BOLD + YELLOW)} : Strategic Consensus ➔ Hierarchical TDD"
        footer_tag = " ◈ .agents   ◈ .codex   ◈ .claude   ◈ 150+ skills "

    top_dashes = max(1, (box_w + 4) - len(header_title) - 3)
    bot_dashes = max(1, (box_w + 4) - len(footer_tag) - 3)

    right_rows = [
        f"{c('╭───', CYAN)}{c(header_title, BOLD + CYAN)}{c('─' * top_dashes + '╮', CYAN)}",
        _box_line(line_1, box_w),
        _box_line(line_2, box_w),
        _box_line(line_3, box_w),
        _box_line(line_4, box_w),
        f"{c('╰───', CYAN)}{c(footer_tag, DIM + CYAN)}{c('─' * bot_dashes + '╯', CYAN)}",
        f"   {c('⚡', YELLOW)} {c('cd ~/project-example && agt', DIM)}",
    ]

    print()
    left_padding = [" " * 28]
    for left, right in zip(ascii_art + left_padding, right_rows):
        print(f"{left}   {right}")


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------
@dataclass
class AgentSpec:
    id: str
    title: str
    role: str
    mission: str
    provider: str  # google | anthropic | openai | multi
    agy_model: str  # VD: gemini-4-argon-high, gemini-3.1-pro-high, gemini-3.8-flash-high, claude-opus-5-5-medium
    claude_model: str  # VD: claude-opus-5-5-medium, sonnet, opus, haiku
    codex_model: str  # VD: gpt-6-astra, gpt-6.1-sol, gpt-6-sol, gpt-6-luna
    reasoning_effort: str  # xhigh | high | medium | low
    context_scope: str
    goal_criteria: str
    enable_write: bool
    enable_subagents: bool
    enable_mcp: bool
    workspace_mode: str  # inherit | share | branch
    agy_tools: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    fallback_chain: List[str] = field(default_factory=list)


@dataclass
class TeamConfig:
    project_name: str
    project_path: str
    tech_stack: str
    project_context: str
    project_goal: str
    extra_rules: List[str]  # VD: Graphify rules, Commit prefix rules, YouTube/domain constraints
    harnesses: List[str]  # ["agy", "codex", "claude"]
    skill_apply_mode: str  # "symlink" | "copy" | "json-only"
    add_commit_restrictions: bool
    selected_skill_bundles: List[str]
    selected_skills: List[Dict[str, str]]
    agents: List[AgentSpec]
    updated_at: str = ""


VI_DIACRITIC_RE = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
    r"ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]"
)


def _is_vi_text(text: str) -> bool:
    return bool(text and VI_DIACRITIC_RE.search(text))


def _matches_current_lang(text: str) -> bool:
    if not text:
        return False
    return _is_vi_text(text) if CURRENT_LANG == "vi" else not _is_vi_text(text)


# ---------------------------------------------------------------------------
# Model & Role Catalogs (Bilingual EN / VI)
# ---------------------------------------------------------------------------
def get_agy_model_choices() -> List[Tuple[str, str]]:
    return [
        (
            "gemini-4-argon-high",
            tr(
                "Google Gemini 4 Argon (High) — Lead Orchestrator / Complex Architecture",
                "Google Gemini 4 Argon (High) — Điều phối viên trưởng / Kiến trúc phức tạp",
            ),
        ),
        (
            "claude-opus-5-5-medium",
            tr(
                "Anthropic Claude Opus 5.5 (Medium) — Lead Orchestrator / Deep Design",
                "Anthropic Claude Opus 5.5 (Medium) — Điều phối viên trưởng / Thiết kế sâu",
            ),
        ),
        (
            "gemini-3.1-pro-high",
            tr(
                "Google Gemini 3.1 Pro (High) — Independent Reviewer & Security",
                "Google Gemini 3.1 Pro (High) — Kiểm định độc lập & Bảo mật",
            ),
        ),
        (
            "gemini-3.8-flash-high",
            tr(
                "Google Gemini 3.8 Flash (High) — Fast & Accurate TDD Implementer",
                "Google Gemini 3.8 Flash (High) — Thực thi code & TDD nhanh, chính xác",
            ),
        ),
        (
            "gemini-3.8-flash-medium",
            tr(
                "Google Gemini 3.8 Flash (Medium) — Focused Searcher & Documentation Scout",
                "Google Gemini 3.8 Flash (Medium) — Trinh sát codebase & Tài liệu",
            ),
        ),
        (
            "gemini-3.7-flash",
            tr(
                "Google Gemini 3.7 Flash (Low) — Lightweight Conventional Committer",
                "Google Gemini 3.7 Flash (Low) — Tạo Git Commit chuẩn Conventional Commits",
            ),
        ),
        (
            "inherit",
            tr(
                "Inherit active session model in Antigravity",
                "Kế thừa model đang mở trong phiên Antigravity",
            ),
        ),
    ]


def get_codex_model_choices() -> List[Tuple[str, str, str]]:
    return [
        (
            "gpt-6-astra",
            "high",
            tr(
                "OpenAI GPT-6 Astra (high) — Main Orchestrator & Integration",
                "OpenAI GPT-6 Astra (high) — Điều phối chính & Tích hợp hệ thống",
            ),
        ),
        (
            "gpt-6.1-sol",
            "xhigh",
            tr(
                "OpenAI GPT-6.1 Sol (xhigh) — Deep Code Review, Security & Async Safety",
                "OpenAI GPT-6.1 Sol (xhigh) — Kiểm định sâu, Bảo mật & An toàn bất đồng bộ",
            ),
        ),
        (
            "gpt-6-sol",
            "xhigh",
            tr(
                "OpenAI GPT-6.0 Sol (xhigh) — Minimal Implementation & TDD Execution",
                "OpenAI GPT-6.0 Sol (xhigh) — Thực thi code tối giản & Chạy TDD",
            ),
        ),
        (
            "gpt-6-luna",
            "medium",
            tr(
                "OpenAI GPT-6 Luna (medium) — Focused Searcher & Documentation Research",
                "OpenAI GPT-6 Luna (medium) — Trinh sát mã nguồn & Tra cứu tài liệu",
            ),
        ),
        (
            "gpt-6-luna-low",
            "low",
            tr(
                "OpenAI GPT-6 Luna (low) — Concise Conventional Committer",
                "OpenAI GPT-6 Luna (low) — Đóng gói Git Commit ngắn gọn",
            ),
        ),
        (
            "gpt-5-codex",
            "high",
            tr(
                "OpenAI GPT-5 Codex (high) — Standard Coding Profile",
                "OpenAI GPT-5 Codex (high) — Cấu hình lập trình tiêu chuẩn",
            ),
        ),
        (
            "o3",
            "high",
            tr(
                "OpenAI o3 (high) — Reasoning & Architecture",
                "OpenAI o3 (high) — Suy luận sâu & Thiết kế kiến trúc",
            ),
        ),
    ]


def get_claude_model_choices() -> List[Tuple[str, str]]:
    return [
        (
            "claude-opus-5-5-medium",
            tr(
                "Claude Opus 5.5 Medium — Orchestrator / Deep Reasoning",
                "Claude Opus 5.5 Medium — Điều phối viên / Suy luận sâu",
            ),
        ),
        (
            "opus",
            tr(
                "Claude Opus — Lead Architect / Reviewer",
                "Claude Opus — Kiến trúc sư trưởng / Kiểm định viên",
            ),
        ),
        (
            "sonnet",
            tr(
                "Claude Sonnet — Implementer / Code Reviewer",
                "Claude Sonnet — Thực thi code / Review mã nguồn",
            ),
        ),
        (
            "haiku",
            tr(
                "Claude Haiku — Fast Searcher / Committer",
                "Claude Haiku — Trinh sát nhanh / Tạo Git Commit",
            ),
        ),
        (
            "inherit",
            tr(
                "Inherit from active Claude Code session",
                "Kế thừa từ phiên Claude Code đang chạy",
            ),
        ),
    ]


def get_cross_provider_fallback_catalog() -> List[Tuple[str, str]]:
    """Unified cross-provider catalog for building ordered model fallback chains."""
    return [
        (
            "agy:gemini-4-argon-high",
            tr(
                "Antigravity — Gemini 4 Argon (High) [Tier: pro]",
                "Antigravity — Gemini 4 Argon (High) [Tier: pro]",
            ),
        ),
        (
            "agy:claude-opus-5-5-medium",
            tr(
                "Antigravity — Claude Opus 5.5 (Medium) [Tier: pro]",
                "Antigravity — Claude Opus 5.5 (Medium) [Tier: pro]",
            ),
        ),
        (
            "agy:gemini-3.1-pro-high",
            tr(
                "Antigravity — Gemini 3.1 Pro (High) [Tier: pro]",
                "Antigravity — Gemini 3.1 Pro (High) [Tier: pro]",
            ),
        ),
        (
            "agy:gemini-3.8-flash-high",
            tr(
                "Antigravity — Gemini 3.8 Flash (High) [Tier: flash]",
                "Antigravity — Gemini 3.8 Flash (High) [Tier: flash]",
            ),
        ),
        (
            "agy:gemini-3.8-flash-medium",
            tr(
                "Antigravity — Gemini 3.8 Flash (Medium) [Tier: flash]",
                "Antigravity — Gemini 3.8 Flash (Medium) [Tier: flash]",
            ),
        ),
        (
            "agy:gemini-3.7-flash",
            tr(
                "Antigravity — Gemini 3.7 Flash (Low) [Tier: flash_lite]",
                "Antigravity — Gemini 3.7 Flash (Low) [Tier: flash_lite]",
            ),
        ),
        (
            "codex:gpt-6.1-sol (xhigh)",
            tr(
                "OpenAI Codex — GPT-6.1 Sol (xhigh)",
                "OpenAI Codex — GPT-6.1 Sol (xhigh)",
            ),
        ),
        (
            "codex:gpt-6-astra (high)",
            tr(
                "OpenAI Codex — GPT-6 Astra (high)",
                "OpenAI Codex — GPT-6 Astra (high)",
            ),
        ),
        (
            "codex:gpt-6-sol (xhigh)",
            tr(
                "OpenAI Codex — GPT-6.0 Sol (xhigh)",
                "OpenAI Codex — GPT-6.0 Sol (xhigh)",
            ),
        ),
        (
            "codex:gpt-6-luna (medium)",
            tr(
                "OpenAI Codex — GPT-6 Luna (medium)",
                "OpenAI Codex — GPT-6 Luna (medium)",
            ),
        ),
        (
            "codex:gpt-6-luna (low)",
            tr(
                "OpenAI Codex — GPT-6 Luna (low)",
                "OpenAI Codex — GPT-6 Luna (low)",
            ),
        ),
        (
            "claude:claude-opus-5-5-medium",
            tr(
                "Claude Code — Claude Opus 5.5 (Medium)",
                "Claude Code — Claude Opus 5.5 (Medium)",
            ),
        ),
        (
            "claude:sonnet",
            tr(
                "Claude Code — Claude Sonnet",
                "Claude Code — Claude Sonnet",
            ),
        ),
        (
            "claude:haiku",
            tr(
                "Claude Code — Claude Haiku",
                "Claude Code — Claude Haiku",
            ),
        ),
    ]


def get_fallback_presets() -> List[Tuple[str, str, List[str]]]:
    """Ready-to-use cross-provider fallback chain presets."""
    return [
        (
            "argon-opus-flash-sol61",
            tr(
                "Argon → Opus 5.5 → 3.8 Flash High → Codex Sol 6.1 (xhigh) [Lead / Deep Reasoning]",
                "Argon → Opus 5.5 → 3.8 Flash High → Codex Sol 6.1 (xhigh) [Điều phối / Suy luận sâu]",
            ),
            [
                "agy:gemini-4-argon-high",
                "agy:claude-opus-5-5-medium",
                "agy:gemini-3.8-flash-high",
                "codex:gpt-6.1-sol (xhigh)",
            ],
        ),
        (
            "pro31-opus-flash-sol61",
            tr(
                "3.1 Pro High → Opus 5.5 → 3.8 Flash High → Codex Sol 6.1 (xhigh) [Reviewer / Security]",
                "3.1 Pro High → Opus 5.5 → 3.8 Flash High → Codex Sol 6.1 (xhigh) [Kiểm định / Bảo mật]",
            ),
            [
                "agy:gemini-3.1-pro-high",
                "agy:claude-opus-5-5-medium",
                "agy:gemini-3.8-flash-high",
                "codex:gpt-6.1-sol (xhigh)",
            ],
        ),
        (
            "designer-flash38-sonnet-sol6",
            tr(
                "3.8 Flash High → 3.1 Pro High → Claude Sonnet → Codex Sol 6.0 (xhigh) [Designer / UI/UX]",
                "3.8 Flash High → 3.1 Pro High → Claude Sonnet → Codex Sol 6.0 (xhigh) [Thiết kế / UI/UX]",
            ),
            [
                "agy:gemini-3.8-flash-high",
                "agy:gemini-3.1-pro-high",
                "claude:sonnet",
                "codex:gpt-6-sol (xhigh)",
            ],
        ),
        (
            "flash38-pro31-sonnet-sol60",
            tr(
                "3.8 Flash High → 3.1 Pro High → Claude Sonnet → Codex Sol 6.0 (xhigh) [Implementer / TDD]",
                "3.8 Flash High → 3.1 Pro High → Claude Sonnet → Codex Sol 6.0 (xhigh) [Thực thi / TDD]",
            ),
            [
                "agy:gemini-3.8-flash-high",
                "agy:gemini-3.1-pro-high",
                "claude:sonnet",
                "codex:gpt-6-sol (xhigh)",
            ],
        ),
        (
            "flash38m-flash38h-haiku-luna",
            tr(
                "3.8 Flash Medium → 3.8 Flash High → Claude Haiku → Codex Luna (medium) [Searcher / Scout]",
                "3.8 Flash Medium → 3.8 Flash High → Claude Haiku → Codex Luna (medium) [Trinh sát / Tài liệu]",
            ),
            [
                "agy:gemini-3.8-flash-medium",
                "agy:gemini-3.8-flash-high",
                "claude:haiku",
                "codex:gpt-6-luna (medium)",
            ],
        ),
        (
            "flash37-flash38m-haiku-lunalow",
            tr(
                "3.7 Flash → 3.8 Flash Medium → Claude Haiku → Codex Luna (low) [Committer / Fast]",
                "3.7 Flash → 3.8 Flash Medium → Claude Haiku → Codex Luna (low) [Git Commit / Nhanh]",
            ),
            [
                "agy:gemini-3.7-flash",
                "agy:gemini-3.8-flash-medium",
                "claude:haiku",
                "codex:gpt-6-luna (low)",
            ],
        ),
    ]


def format_fallback_chain(chain: List[str]) -> str:
    if not chain:
        return tr("None", "Chưa thiết lập")
    return " → ".join(chain)


READ_WRITE_TOOLS = [
    "read_file",
    "edit_file",
    "write_file",
    "run_command",
    "manage_task",
]

REVIEWER_TOOLS = [
    "read_file",
    "run_command",
    "manage_task",
]

SEARCHER_TOOLS = [
    "read_file",
    "run_command",
    "search_web",
]

COMMITTER_TOOLS = [
    "read_file",
    "run_command",
    "manage_task",
]

LEAD_ARCHITECT_TOOLS = [
    "read_file",
    "run_command",
    "manage_task",
    "search_web",
]

LEAD_CRITIC_TOOLS = [
    "read_file",
    "run_command",
    "manage_task",
]

ORCHESTRATOR_TOOLS = [
    "read_file",
    "run_command",
    "manage_task",
    "invoke_subagent",
    "send_message",
    "manage_subagents",
    "define_subagent",
]

ANTIGRAVITY_CANONICAL_TOOL_MAP: Dict[str, str] = {
    "view_file": "read_file",
    "grep_search": "read_file",
    "find_by_name": "read_file",
    "list_dir": "read_file",
    "write_to_file": "write_file",
    "replace_file_content": "edit_file",
    "multi_replace_file_content": "edit_file",
    "read_url_content": "search_web",
}

DISALLOWED_WRITE_TOOLS = {
    "edit_file",
    "write_file",
    "write_to_file",
    "replace_file_content",
    "multi_replace_file_content",
}


def canonicalize_antigravity_tools(tools: Sequence[str], enable_write: bool = True) -> List[str]:
    """
    Map legacy tool names to Antigravity 2.0 canonical tool names,
    deduplicating while preserving order, and stripping write tools if enable_write is False.
    """
    seen = set()
    canonical: List[str] = []
    for t in tools:
        resolved = ANTIGRAVITY_CANONICAL_TOOL_MAP.get(t, t)
        if not enable_write and resolved in DISALLOWED_WRITE_TOOLS:
            continue
        if resolved not in seen:
            seen.add(resolved)
            canonical.append(resolved)
    return canonical

DEFAULT_AGENT_TEMPLATES_EN: Dict[str, Dict] = {
    "lead-architect": {
        "title": "Argon / Astra: Lead Solution Architecture & Strategic Planning",
        "role": "Lead Solution Architect & Planner",
        "mission": (
            "Formulate initial architecture proposals, technical design blueprints, module contracts, and task "
            "breakdowns. Defend and refine the plan across 2 structured debate rounds with lead-critic until consensus "
            "is reached, then hand off the approved blueprint to the orchestrator for execution."
        ),
        "provider": "multi",
        "agy_model": "gemini-4-argon-high",
        "claude_model": "claude-opus-5-5-medium",
        "codex_model": "gpt-6-astra",
        "reasoning_effort": "high",
        "context_scope": "Full repository architecture, domain models, technical constraints, and requirement specifications.",
        "goal_criteria": (
            "Deliver a modular, decoupled design proposal; address all critique points raised by lead-critic within 2 debate "
            "rounds; produce an actionable task breakdown for orchestrator."
        ),
        "enable_write": False,
        "enable_subagents": False,
        "enable_mcp": True,
        "workspace_mode": "inherit",
        "agy_tools": list(LEAD_ARCHITECT_TOOLS),
        "skills": [
            "brainstorming",
            "writing-plans",
            "codebase-design",
            "domain-modeling",
            "research",
        ],
        "fallback_chain": [
            "agy:gemini-4-argon-high",
            "agy:claude-opus-5-5-medium",
            "agy:gemini-3.8-flash-high",
            "codex:gpt-6-astra (high)",
        ],
    },
    "lead-critic": {
        "title": "3.1 Pro High / Sol 6.1: Lead Technical Critic & Challenger",
        "role": "Lead Technical Critic & Challenger",
        "mission": (
            "Stress-test architecture and design proposals in a bounded 2-round debate with lead-architect. "
            "Identify hidden assumptions, concurrency/security risks, scalability bottlenecks, and YAGNI/over-engineering. "
            "Issue final sign-off (CONSENSUS_REACHED) only when all critical concerns are resolved."
        ),
        "provider": "multi",
        "agy_model": "gemini-3.1-pro-high",
        "claude_model": "claude-opus-5-5-medium",
        "codex_model": "gpt-6.1-sol",
        "reasoning_effort": "xhigh",
        "context_scope": "Architecture proposals from lead-architect, system constraints, threat models, and code quality benchmarks.",
        "goal_criteria": (
            "Provide rigorous, actionable critique in Round 1; verify all risks are mitigated in Round 2; "
            "grant explicit CONSENSUS_REACHED or report blocking architectural flaws."
        ),
        "enable_write": False,
        "enable_subagents": False,
        "enable_mcp": False,
        "workspace_mode": "inherit",
        "agy_tools": list(LEAD_CRITIC_TOOLS),
        "skills": [
            "grilling",
            "code-review",
            "ponytail-review",
            "ponytail-audit",
            "codebase-design",
        ],
        "fallback_chain": [
            "agy:gemini-3.1-pro-high",
            "agy:claude-opus-5-5-medium",
            "agy:gemini-3.8-flash-high",
            "codex:gpt-6.1-sol (xhigh)",
        ],
    },
    "orchestrator": {
        "title": "Astra / Argon: Execution Orchestration & Worker Dispatcher",
        "role": "Lead Execution Orchestrator",
        "mission": (
            "Receive the finalized architecture blueprint approved from the 2-round lead debate (lead-architect ⮂ lead-critic). "
            "Coordinate execution across worker subagents: allow parallel fan-out for independent codebase reads (searcher); "
            "keep shared-file implementation (implementer, designer), independent verification (reviewer), and commits (committer) "
            "strictly ordered. Verify overall integration without modifying production code directly."
        ),
        "provider": "multi",
        "agy_model": "gemini-4-argon-high",
        "claude_model": "claude-opus-5-5-medium",
        "codex_model": "gpt-6-astra",
        "reasoning_effort": "high",
        "context_scope": "Approved design blueprint, repository architecture, AGENTS.md, module contracts, and worker task statuses.",
        "goal_criteria": (
            "Single-writer file boundaries across implementer and designer; all reviewer findings resolved; "
            "full application builds and passes tests before claiming completion."
        ),
        "enable_write": False,
        "enable_subagents": True,
        "enable_mcp": True,
        "workspace_mode": "inherit",
        "agy_tools": list(ORCHESTRATOR_TOOLS),
        "skills": [
            "subagent-driven-development",
            "dispatching-parallel-agents",
            "executing-plans",
            "verification-before-completion",
            "swarm",
        ],
        "fallback_chain": [
            "agy:gemini-4-argon-high",
            "agy:claude-opus-5-5-medium",
            "agy:gemini-3.8-flash-high",
            "codex:gpt-6.1-sol (xhigh)",
        ],
    },
    "reviewer": {
        "title": "3.1 Pro High / Sol 6.1: Code Correctness, Security & Test Quality Review",
        "role": "Independent Code Quality & Security Reviewer",
        "mission": (
            "Independently review changes in read-only mode: detect logic bugs, async race conditions, "
            "security vulnerabilities, unvalidated inputs, and missing regression tests. "
            "Report actionable defects with exact file/line, impact, and smallest safe fix."
        ),
        "provider": "multi",
        "agy_model": "gemini-3.1-pro-high",
        "claude_model": "sonnet",
        "codex_model": "gpt-6.1-sol",
        "reasoning_effort": "xhigh",
        "context_scope": "Read-only inspection of git diffs, affected modules, and test suites.",
        "goal_criteria": (
            "Distinguish verified behavior from assumptions; cite exact file:line for every finding; "
            "do not overwrite files directly unless explicitly assigned to fix a specific bug."
        ),
        "enable_write": False,
        "enable_subagents": False,
        "enable_mcp": False,
        "workspace_mode": "inherit",
        "agy_tools": list(REVIEWER_TOOLS),
        "skills": [
            "code-review",
            "ponytail-review",
            "ponytail-audit",
            "requesting-code-review",
        ],
        "fallback_chain": [
            "agy:gemini-3.1-pro-high",
            "agy:claude-opus-5-5-medium",
            "agy:gemini-3.8-flash-high",
            "codex:gpt-6.1-sol (xhigh)",
        ],
    },
    "designer": {
        "title": "Flash-3.8 / Sol 6: UI/UX & Anti-Slop Visual Designer",
        "role": "UI/UX & Anti-Slop Visual Designer",
        "mission": (
            "Design and implement pixel-perfect, anti-slop frontend interfaces, UI components, animations, "
            "and visual assets adhering to strict design taste and design systems."
        ),
        "provider": "multi",
        "agy_model": "gemini-3.8-flash-high",
        "claude_model": "sonnet",
        "codex_model": "gpt-6-sol",
        "reasoning_effort": "high",
        "context_scope": "Frontend components, styles, design tokens, UI templates, design system guidelines, and user experience assets.",
        "goal_criteria": (
            "Deliver high-end, responsive, accessible, and anti-slop visual designs and components with clean code and token adherence."
        ),
        "enable_write": True,
        "enable_subagents": False,
        "enable_mcp": True,
        "workspace_mode": "share",
        "agy_tools": list(READ_WRITE_TOOLS),
        "skills": [
            "design-taste-frontend",
            "ui-ux-pro-max",
            "ui-styling",
            "design-system",
            "design",
            "brand",
            "banner-design",
            "slides",
        ],
        "fallback_chain": [
            "agy:gemini-3.8-flash-high",
            "agy:gemini-3.1-pro-high",
            "claude:sonnet",
            "codex:gpt-6-sol (xhigh)",
        ],
    },
    "implementer": {
        "title": "3.8 Flash High / Sol 6.0: Minimal Implementation, TDD & Test Execution",
        "role": "Senior Feature & TDD Implementer",
        "mission": (
            "Implement and test with the smallest complete changes: write regression/unit tests first, "
            "run them to verify failure (Red), implement the minimal code to pass (Green), and refactor."
        ),
        "provider": "multi",
        "agy_model": "gemini-3.8-flash-high",
        "claude_model": "sonnet",
        "codex_model": "gpt-6-sol",
        "reasoning_effort": "xhigh",
        "context_scope": "Assigned modules/files in the task brief and corresponding test suites.",
        "goal_criteria": (
            "Follow existing module contracts and architecture; preserve error handling and resource cleanup; "
            "report actual commands executed and verified test results."
        ),
        "enable_write": True,
        "enable_subagents": False,
        "enable_mcp": True,
        "workspace_mode": "share",
        "agy_tools": list(READ_WRITE_TOOLS),
        "skills": [
            "test-driven-development",
            "tdd",
            "ponytail",
            "codebase-design",
            "systematic-debugging",
            "verification-before-completion",
        ],
        "fallback_chain": [
            "agy:gemini-3.8-flash-high",
            "agy:gemini-3.1-pro-high",
            "claude:sonnet",
            "codex:gpt-6-sol (xhigh)",
        ],
    },
    "searcher": {
        "title": "Luna / 3.8 Flash Medium: Focused Research & Codebase Scout",
        "role": "Primary Documentation & Codebase Scout",
        "mission": (
            "Research focused questions against primary documentation and scout the codebase in read-only mode. "
            "Return concise findings with direct URLs, API signatures, exact file:line paths, and compatibility limits."
        ),
        "provider": "multi",
        "agy_model": "gemini-3.8-flash-medium",
        "claude_model": "haiku",
        "codex_model": "gpt-6-luna",
        "reasoning_effort": "medium",
        "context_scope": "Read-only access across codebase, local docs, and primary web documentation.",
        "goal_criteria": (
            "Verify facts before recommending dependencies or configuration; never modify code "
            "or include secrets in search queries."
        ),
        "enable_write": False,
        "enable_subagents": False,
        "enable_mcp": True,
        "workspace_mode": "inherit",
        "agy_tools": list(SEARCHER_TOOLS),
        "skills": [
            "research",
            "domain-modeling",
            "diagnosing-bugs",
        ],
        "fallback_chain": [
            "agy:gemini-3.8-flash-medium",
            "agy:gemini-3.8-flash-high",
            "claude:haiku",
            "codex:gpt-6-luna (medium)",
        ],
    },
    "committer": {
        "title": "3.7 Flash Low / Luna: Concise Conventional Git Commits",
        "role": "Conventional Git Committer",
        "mission": (
            "Inspect git status (`git status -s`, `git diff --staged`) and craft concise, professional "
            "commit messages in Conventional Commits format (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`)."
        ),
        "provider": "multi",
        "agy_model": "gemini-3.7-flash",
        "claude_model": "haiku",
        "codex_model": "gpt-6-luna",
        "reasoning_effort": "low",
        "context_scope": "Git working tree, staged changes, and commit history.",
        "goal_criteria": (
            "Imperative mood subject line, lowercase, 50-72 chars max, no trailing period; "
            "atomic commits; never stage or commit secrets, credentials, or local config files."
        ),
        "enable_write": False,
        "enable_subagents": False,
        "enable_mcp": False,
        "workspace_mode": "inherit",
        "agy_tools": list(COMMITTER_TOOLS),
        "skills": [
            "finishing-a-development-branch",
            "pr",
        ],
        "fallback_chain": [
            "agy:gemini-3.7-flash",
            "agy:gemini-3.8-flash-medium",
            "claude:haiku",
            "codex:gpt-6-luna (low)",
        ],
    },
}

DEFAULT_AGENT_TEMPLATES_VI: Dict[str, Dict] = {
    "lead-architect": {
        "title": "Argon / Astra: Kiến trúc sư trưởng & Hoạch định chiến lược",
        "role": "Kiến trúc sư trưởng & Hoạch định giải pháp",
        "mission": (
            "Xây dựng đề xuất kiến trúc sơ bộ, thông số kỹ thuật (RFC), hợp đồng module và kế hoạch phân rã nhiệm vụ. "
            "Bảo vệ và tinh chỉnh giải pháp qua 2 vòng phản biện kỹ thuật chặt chẽ với lead-critic đến khi đạt đồng thuận, "
            "sau đó bàn giao bản thiết kế hoàn thiện cho orchestrator điều phối thực thi."
        ),
        "provider": "multi",
        "agy_model": "gemini-4-argon-high",
        "claude_model": "claude-opus-5-5-medium",
        "codex_model": "gpt-6-astra",
        "reasoning_effort": "high",
        "context_scope": "Toàn bộ kiến trúc repo, mô hình miền (domain model), ràng buộc kỹ thuật và yêu cầu bài toán.",
        "goal_criteria": (
            "Xuất bản đề xuất kiến trúc mô-đun hóa sâu, rõ ràng; giải quyết thỏa đáng toàn bộ phản biện từ lead-critic "
            "trong đúng 2 vòng phản biện để đạt CONSENSUS_REACHED; bàn giao kế hoạch phân rã khả thi cho orchestrator."
        ),
        "enable_write": False,
        "enable_subagents": False,
        "enable_mcp": True,
        "workspace_mode": "inherit",
        "agy_tools": list(LEAD_ARCHITECT_TOOLS),
        "skills": [
            "brainstorming",
            "writing-plans",
            "codebase-design",
            "domain-modeling",
            "research",
        ],
        "fallback_chain": [
            "agy:gemini-4-argon-high",
            "agy:claude-opus-5-5-medium",
            "agy:gemini-3.8-flash-high",
            "codex:gpt-6-astra (high)",
        ],
    },
    "lead-critic": {
        "title": "3.1 Pro High / Sol 6.1: Phản biện trưởng & Thẩm định rủi ro",
        "role": "Phản biện trưởng & Thẩm định rủi ro kỹ thuật",
        "mission": (
            "Kiểm thử áp lực (stress-test) các đề xuất kiến trúc và kế hoạch phân rã từ lead-architect qua 2 vòng phản biện. "
            "Vạch rõ điểm mù, rủi ro bảo mật, nghẽn hiệu năng, và loại bỏ sự phức tạp hóa thừa thãi (YAGNI/Over-engineering). "
            "Chỉ phê duyệt và cấp chứng nhận đồng thuận (CONSENSUS_REACHED) khi kế hoạch đạt độ tin cậy và an toàn cao."
        ),
        "provider": "multi",
        "agy_model": "gemini-3.1-pro-high",
        "claude_model": "claude-opus-5-5-medium",
        "codex_model": "gpt-6.1-sol",
        "reasoning_effort": "xhigh",
        "context_scope": "Đề xuất kiến trúc của lead-architect, ràng buộc hệ thống, mô hình đe dọa (threat model) và tiêu chuẩn chất lượng code.",
        "goal_criteria": (
            "Đưa ra danh sách phản biện sắc bén, có dẫn chứng tại Vòng 1; thẩm định lại bản sửa đổi tại Vòng 2; "
            "chỉ cấp CONSENSUS_REACHED khi mọi rủi ro đã được hóa giải hoặc cảnh báo rõ rủi ro chặn (blocking flaws)."
        ),
        "enable_write": False,
        "enable_subagents": False,
        "enable_mcp": False,
        "workspace_mode": "inherit",
        "agy_tools": list(LEAD_CRITIC_TOOLS),
        "skills": [
            "grilling",
            "code-review",
            "ponytail-review",
            "ponytail-audit",
            "codebase-design",
        ],
        "fallback_chain": [
            "agy:gemini-3.1-pro-high",
            "agy:claude-opus-5-5-medium",
            "agy:gemini-3.8-flash-high",
            "codex:gpt-6.1-sol (xhigh)",
        ],
    },
    "orchestrator": {
        "title": "Astra / Argon: Tổng điều phối thực thi & Phân công Subagents",
        "role": "Tổng điều phối viên thực thi",
        "mission": (
            "Tiếp nhận bản thiết kế kiến trúc hoàn thiện đã đạt đồng thuận từ cặp Lead phản biện (lead-architect ⮂ lead-critic). "
            "Điều phối thực thi phân cấp: cho phép fan-out các tác vụ đọc độc lập (searcher); giữ các tác vụ sửa file chung "
            "(implementer, designer), kiểm định độc lập (reviewer) và commit (committer) theo đúng thứ tự tuần tự. "
            "Giữ vai trò kiểm chứng tích hợp, không tự sửa code sản phẩm trực tiếp."
        ),
        "provider": "multi",
        "agy_model": "gemini-4-argon-high",
        "claude_model": "claude-opus-5-5-medium",
        "codex_model": "gpt-6-astra",
        "reasoning_effort": "high",
        "context_scope": "Bản thiết kế kiến trúc đã thống nhất, AGENTS.md, hợp đồng module và trạng thái tiến độ các worker.",
        "goal_criteria": (
            "Ranh giới tệp đơn ghi (single-writer) rõ ràng giữa implementer và designer; mọi phát hiện của reviewer được xử lý triệt để; "
            "toàn bộ test suite vượt qua hoàn toàn trước khi báo cáo hoàn thành."
        ),
        "enable_write": False,
        "enable_subagents": True,
        "enable_mcp": True,
        "workspace_mode": "inherit",
        "agy_tools": list(ORCHESTRATOR_TOOLS),
        "skills": [
            "subagent-driven-development",
            "dispatching-parallel-agents",
            "executing-plans",
            "verification-before-completion",
            "swarm",
        ],
        "fallback_chain": [
            "agy:gemini-4-argon-high",
            "agy:claude-opus-5-5-medium",
            "agy:gemini-3.8-flash-high",
            "codex:gpt-6.1-sol (xhigh)",
        ],
    },
    "reviewer": {
        "title": "3.1 Pro High / Sol 6.1: Kiểm định chất lượng code, Bảo mật & Kiểm thử",
        "role": "Kiểm định viên chất lượng & Bảo mật độc lập",
        "mission": (
            "Kiểm định độc lập các thay đổi ở chế độ chỉ đọc: phát hiện lỗi logic, xung đột bất đồng bộ, "
            "lỗ hổng bảo mật, đầu vào chưa kiểm tra và thiếu bài test hồi quy. "
            "Báo cáo rõ file:dòng, mức độ ảnh hưởng và hướng sửa nhỏ gọn, an toàn nhất."
        ),
        "provider": "multi",
        "agy_model": "gemini-3.1-pro-high",
        "claude_model": "sonnet",
        "codex_model": "gpt-6.1-sol",
        "reasoning_effort": "xhigh",
        "context_scope": "Kiểm tra chỉ đọc trên git diff, các module bị ảnh hưởng và bộ kiểm thử.",
        "goal_criteria": (
            "Phân biệt rõ hành vi đã kiểm chứng với giả định; dẫn chứng chính xác file:dòng cho từng phát hiện; "
            "không tự ý ghi đè file trừ khi được giao sửa một lỗi cụ thể."
        ),
        "enable_write": False,
        "enable_subagents": False,
        "enable_mcp": False,
        "workspace_mode": "inherit",
        "agy_tools": list(REVIEWER_TOOLS),
        "skills": [
            "code-review",
            "ponytail-review",
            "ponytail-audit",
            "requesting-code-review",
        ],
        "fallback_chain": [
            "agy:gemini-3.1-pro-high",
            "agy:claude-opus-5-5-medium",
            "agy:gemini-3.8-flash-high",
            "codex:gpt-6.1-sol (xhigh)",
        ],
    },
    "designer": {
        "title": "Flash-3.8 / Sol 6: Kỹ sư thiết kế UI/UX & Bản sắc thị giác Anti-Slop",
        "role": "Kỹ sư thiết kế UI/UX & Bản sắc thị giác Anti-Slop",
        "mission": (
            "Thiết kế và triển khai giao diện frontend chuẩn mực, loại bỏ slop, đảm bảo tính thẩm mỹ pixel-perfect, "
            "design system và trải nghiệm người dùng cao cấp."
        ),
        "provider": "multi",
        "agy_model": "gemini-3.8-flash-high",
        "claude_model": "sonnet",
        "codex_model": "gpt-6-sol",
        "reasoning_effort": "high",
        "context_scope": "Thành phần giao diện (UI components), styles, design tokens, mẫu layout, quy chuẩn thiết kế và tài nguyên đồ họa.",
        "goal_criteria": (
            "Tạo ra giao diện sắc nét, đáp ứng tốt, truy cập chuẩn (a11y) và loại bỏ hoàn toàn các lỗi slop phổ biến với code sạch và token nhất quán."
        ),
        "enable_write": True,
        "enable_subagents": False,
        "enable_mcp": True,
        "workspace_mode": "share",
        "agy_tools": list(READ_WRITE_TOOLS),
        "skills": [
            "design-taste-frontend",
            "ui-ux-pro-max",
            "ui-styling",
            "design-system",
            "design",
            "brand",
            "banner-design",
            "slides",
        ],
        "fallback_chain": [
            "agy:gemini-3.8-flash-high",
            "agy:gemini-3.1-pro-high",
            "claude:sonnet",
            "codex:gpt-6-sol (xhigh)",
        ],
    },
    "implementer": {
        "title": "3.8 Flash High / Sol 6.0: Thực thi tối giản, TDD & Chạy kiểm thử",
        "role": "Kỹ sư thực thi tính năng & TDD",
        "mission": (
            "Thực thi và kiểm thử với thay đổi nhỏ gọn, trọn vẹn nhất: viết bài test đơn vị/hồi quy trước, "
            "chạy xác nhận fail (Red), viết code tối thiểu để vượt qua bài test (Green) và làm sạch code."
        ),
        "provider": "multi",
        "agy_model": "gemini-3.8-flash-high",
        "claude_model": "sonnet",
        "codex_model": "gpt-6-sol",
        "reasoning_effort": "xhigh",
        "context_scope": "Các module/file được phân công trong tác vụ và bộ kiểm thử tương ứng.",
        "goal_criteria": (
            "Tuân thủ kiến trúc và hợp đồng module hiện có; bảo toàn xử lý lỗi và giải phóng tài nguyên; "
            "báo cáo trung thực câu lệnh đã chạy và kết quả kiểm thử thực tế."
        ),
        "enable_write": True,
        "enable_subagents": False,
        "enable_mcp": True,
        "workspace_mode": "share",
        "agy_tools": list(READ_WRITE_TOOLS),
        "skills": [
            "test-driven-development",
            "tdd",
            "ponytail",
            "codebase-design",
            "systematic-debugging",
            "verification-before-completion",
        ],
        "fallback_chain": [
            "agy:gemini-3.8-flash-high",
            "agy:gemini-3.1-pro-high",
            "claude:sonnet",
            "codex:gpt-6-sol (xhigh)",
        ],
    },
    "searcher": {
        "title": "Luna / 3.8 Flash Medium: Trinh sát mã nguồn & Tra cứu tài liệu",
        "role": "Trinh sát mã nguồn & Tài liệu chính thống",
        "mission": (
            "Tra cứu các câu hỏi trọng tâm trên tài liệu chính thống và khảo sát codebase ở chế độ chỉ đọc. "
            "Trả về báo cáo cô đọng kèm URL, chữ ký API, đường dẫn file:dòng và các giới hạn tương thích."
        ),
        "provider": "multi",
        "agy_model": "gemini-3.8-flash-medium",
        "claude_model": "haiku",
        "codex_model": "gpt-6-luna",
        "reasoning_effort": "medium",
        "context_scope": "Truy cập chỉ đọc trên toàn bộ codebase, tài liệu cục bộ và tài liệu web chính thống.",
        "goal_criteria": (
            "Xác minh thông tin trước khi đề xuất thư viện hoặc cấu hình; tuyệt đối không sửa đổi code "
            "và không đưa thông tin nhạy cảm vào truy vấn tìm kiếm."
        ),
        "enable_write": False,
        "enable_subagents": False,
        "enable_mcp": True,
        "workspace_mode": "inherit",
        "agy_tools": list(SEARCHER_TOOLS),
        "skills": [
            "research",
            "domain-modeling",
            "diagnosing-bugs",
        ],
        "fallback_chain": [
            "agy:gemini-3.8-flash-medium",
            "agy:gemini-3.8-flash-high",
            "claude:haiku",
            "codex:gpt-6-luna (medium)",
        ],
    },
    "committer": {
        "title": "3.7 Flash Low / Luna: Tạo Git Commit chuẩn Conventional Commits",
        "role": "Chuyên viên đóng gói Git Commit",
        "mission": (
            "Kiểm tra trạng thái git (`git status -s`, `git diff --staged`) và soạn thông điệp commit "
            "ngắn gọn, chuẩn Conventional Commits (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`)."
        ),
        "provider": "multi",
        "agy_model": "gemini-3.7-flash",
        "claude_model": "haiku",
        "codex_model": "gpt-6-luna",
        "reasoning_effort": "low",
        "context_scope": "Cây thư mục git, các thay đổi đã stage và lịch sử commit.",
        "goal_criteria": (
            "Tiêu đề ở thể mệnh lệnh, chữ thường, tối đa 50-72 ký tự, không dấu chấm cuối; "
            "commit nguyên tử; tuyệt đối không stage hoặc commit secrets hay file cấu hình nhạy cảm."
        ),
        "enable_write": False,
        "enable_subagents": False,
        "enable_mcp": False,
        "workspace_mode": "inherit",
        "agy_tools": list(COMMITTER_TOOLS),
        "skills": [
            "finishing-a-development-branch",
            "pr",
        ],
        "fallback_chain": [
            "agy:gemini-3.7-flash",
            "agy:gemini-3.8-flash-medium",
            "claude:haiku",
            "codex:gpt-6-luna (low)",
        ],
    },
}


def get_agent_templates() -> Dict[str, Dict]:
    return DEFAULT_AGENT_TEMPLATES_VI if CURRENT_LANG == "vi" else DEFAULT_AGENT_TEMPLATES_EN


SKILL_BUNDLES: Dict[str, Dict[str, object]] = {
    "core-subagents-tdd": {
        "label_en": "Core Subagents, Planning & TDD",
        "label_vi": "Điều phối Subagents, Lập kế hoạch & TDD cốt lõi",
        "description_en": "Subagent orchestration, planning, TDD, systematic debugging, and two-axis code review.",
        "description_vi": "Điều phối subagents, lập kế hoạch, TDD, gỡ lỗi có hệ thống và kiểm định code 2 trục.",
        "skills": [
            "brainstorming",
            "writing-plans",
            "executing-plans",
            "subagent-driven-development",
            "dispatching-parallel-agents",
            "test-driven-development",
            "systematic-debugging",
            "verification-before-completion",
            "requesting-code-review",
            "receiving-code-review",
            "code-review",
            "tdd",
            "codebase-design",
            "diagnosing-bugs",
            "research",
            "grilling",
            "writing-for-agents",
        ],
    },
    "ponytail-lean": {
        "label_en": "Ponytail Lean / YAGNI Senior Mode",
        "label_vi": "Chế độ Ponytail Tinh gọn / YAGNI",
        "description_en": "Minimalist code changes, anti-overengineering, pragmatic review, and tech debt auditing.",
        "description_vi": "Code tối giản, chống phức tạp hóa, review thực dụng và kiểm toán nợ kỹ thuật.",
        "skills": [
            "ponytail",
            "ponytail-review",
            "ponytail-audit",
            "ponytail-debt",
            "ponytail-help",
        ],
    },
    "frontend-taste-ui": {
        "label_en": "Frontend Taste & UI/UX Pro Max",
        "label_vi": "Thiết kế Giao diện Frontend & UI/UX Pro Max",
        "description_en": "Anti-slop art direction, minimalist/brutalist UI, motion design, and shadcn/tailwind.",
        "description_vi": "Định hướng thẩm mỹ cao cấp, UI tối giản/brutalist, chuyển động mượt và shadcn/tailwind.",
        "skills": [
            "design-taste-frontend",
            "ui-ux-pro-max",
            "ui-styling",
            "design-system",
            "design",
            "brand",
            "banner-design",
            "slides",
            "minimalist-ui",
            "high-end-visual-design",
            "gpt-taste",
            "stitch-design-taste",
            "design-motion-principles",
            "improve-animations",
            "review-animations",
        ],
    },
    "architecture-archify": {
        "label_en": "Architecture Diagrams, Domain Modeling & Playwright",
        "label_vi": "Sơ đồ Kiến trúc, Mô hình hóa Miền & Playwright",
        "description_en": "Interactive architecture diagrams, domain modeling, and Playwright verification.",
        "description_vi": "Sơ đồ kiến trúc trực quan, thiết kế domain model và kiểm thử tự động Playwright.",
        "skills": [
            "archify",
            "domain-modeling",
            "playwright-cli",
            "full-output-enforcement",
            "pr",
            "humanizer",
        ],
    },
    "agy-swarm": {
        "label_en": "Antigravity Native Swarm & Customizations",
        "label_vi": "Antigravity Native Swarm & Tùy biến Hệ thống",
        "description_en": "Parallel multi-agent swarm message board and Antigravity customization guides.",
        "description_vi": "Điều phối bầy đàn đa tác tử song song và hướng dẫn tùy biến Antigravity.",
        "skills": [
            "swarm",
            "agy-customizations",
            "antigravity-guide",
        ],
    },
}


# ---------------------------------------------------------------------------
# Environment & Skill Discovery (Quét cả ~/.gemini và ~/Projects/Hephaestus/.agents/skills)
# ---------------------------------------------------------------------------
def discover_local_skills() -> Dict[str, Dict[str, str]]:
    """
    Quét toàn bộ SKILL.md có sẵn trên máy:
      - ~/.gemini/config/plugins
      - ~/.gemini/antigravity-cli/builtin/skills
      - ~/Projects/Hephaestus/.agents/skills (Kho skills mở rộng cực xịn của user)
    """
    home = Path.home()
    search_roots = [
        (home / ".gemini" / "config" / "plugins", "gemini-plugin"),
        (home / "Projects" / "Hephaestus" / ".agents" / "skills", "hephaestus-skills"),
        (home / ".gemini" / "antigravity-cli" / "builtin" / "skills", "agy-builtin"),
    ]
    discovered: Dict[str, Dict[str, str]] = {}

    for root, source_type in search_roots:
        if not root.exists():
            continue
        for skill_md in root.rglob("SKILL.md"):
            path_str = str(skill_md)
            if "/cli/assets/" in path_str or "/.openclaw/" in path_str:
                continue

            skill_dir = skill_md.parent
            parent_dir = skill_dir.parent
            skill_name = skill_dir.name
            description = ""

            try:
                content = skill_md.read_text(encoding="utf-8", errors="ignore")
                m_name = re.search(r"^name:\s*([^\n]+)", content, re.MULTILINE)
                if m_name:
                    parsed_name = m_name.group(1).strip().strip("'\"")
                    if parsed_name:
                        skill_name = parsed_name
                m_desc = re.search(r"^description:\s*>?-?\s*\n?\s*([^\n]+)", content, re.MULTILINE)
                if m_desc:
                    description = m_desc.group(1).strip().strip("'\"")
            except Exception:
                pass

            plugin_name = source_type
            if source_type == "gemini-plugin" and "plugins" in skill_md.parts:
                idx = skill_md.parts.index("plugins")
                if idx + 1 < len(skill_md.parts):
                    plugin_name = skill_md.parts[idx + 1]

            if skill_name not in discovered:
                discovered[skill_name] = {
                    "name": skill_name,
                    "plugin": plugin_name,
                    "skill_dir": str(skill_dir),
                    "parent_dir": str(parent_dir),
                    "description": description,
                }

    return discovered


def detect_tech_stack(project_path: Path) -> str:
    indicators = []
    if (project_path / "package.json").exists():
        indicators.append("Node.js / TypeScript / JavaScript")
    if (project_path / "pyproject.toml").exists() or (project_path / "requirements.txt").exists():
        indicators.append("Python")
    elif list(project_path.glob("*.py")):
        indicators.append("Python")
    if (project_path / "Cargo.toml").exists():
        indicators.append("Rust")
    if (project_path / "go.mod").exists():
        indicators.append("Go")
    if (project_path / "CMakeLists.txt").exists() or (project_path / "Makefile").exists():
        indicators.append("C/C++ / Make")
    if (project_path / "docker-compose.yml").exists() or (project_path / "Dockerfile").exists():
        indicators.append("Docker")
    return " + ".join(indicators) if indicators else "General Software Project"


# ---------------------------------------------------------------------------
# Interactive Prompt Helpers
# ---------------------------------------------------------------------------
def ask_text(prompt_label: str, default: str = "") -> str:
    default_hint = f" [{c(default, CYAN)}]" if default else ""
    try:
        val = input(f"{c('?', BOLD + GREEN)} {BOLD}{prompt_label}{RESET}{default_hint}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print(tr("\nSetup cancelled.", "\nĐã hủy thiết lập."))
        sys.exit(0)
    return val if val else default


def ask_yes_no(prompt_label: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    try:
        val = input(f"{c('?', BOLD + GREEN)} {BOLD}{prompt_label}{RESET} [{c(hint, CYAN)}]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print(tr("\nSetup cancelled.", "\nĐã hủy thiết lập."))
        sys.exit(0)
    if not val:
        return default
    return val in ("y", "yes", "co", "có", "1", "true")


def ask_choice(prompt_label: str, options: List[Tuple[str, str]], default_index: int = 0) -> str:
    print(f"\n{c('?', BOLD + GREEN)} {BOLD}{prompt_label}{RESET}")
    for idx, (key, desc) in enumerate(options, start=1):
        marker = c(tr(" (default)", " (mặc định)"), YELLOW) if (idx - 1) == default_index else ""
        print(f"  {c(str(idx), BOLD + CYAN)}. {BOLD}{key}{RESET} — {desc}{marker}")
    raw = ask_text(tr("Select number (or type name)", "Chọn số (hoặc nhập trực tiếp tên)"), str(default_index + 1))
    if raw.isdigit():
        num = int(raw)
        if 1 <= num <= len(options):
            return options[num - 1][0]
    for key, _ in options:
        if raw.lower() == key.lower():
            return key
    return raw


def ask_multi_choice(
    prompt_label: str,
    options: List[Tuple[str, str]],
    default_indices: List[int],
) -> List[str]:
    print(f"\n{c('?', BOLD + GREEN)} {BOLD}{prompt_label}{RESET}")
    for idx, (key, desc) in enumerate(options, start=1):
        checked = c("[✓]", GREEN) if (idx - 1) in default_indices else c("[ ]", DIM)
        print(f"  {c(str(idx), BOLD + CYAN)}. {checked} {BOLD}{key}{RESET} — {desc}")
    default_str = ",".join(str(i + 1) for i in default_indices)
    raw = ask_text(
        tr(
            "Enter comma-separated numbers (or 'all' / Enter for default)",
            "Nhập các số cách nhau bằng dấu phẩy (hoặc 'all' / Enter để giữ mặc định)",
        ),
        default_str,
    )
    if raw.lower() == "all":
        return [k for k, _ in options]
    chosen: List[str] = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(options):
                key = options[idx][0]
                if key not in chosen:
                    chosen.append(key)
        else:
            for key, _ in options:
                if part.lower() == key.lower() and key not in chosen:
                    chosen.append(key)
    return chosen if chosen else [options[i][0] for i in default_indices]


# ---------------------------------------------------------------------------
# Wizard Logic
# ---------------------------------------------------------------------------
def select_project_directory(initial_dir: Path, projects_root: Path) -> Path:
    resolved = initial_dir.resolve()
    if resolved != projects_root.resolve():
        is_self_repo = resolved == Path(__file__).resolve().parent
        use_current = ask_yes_no(
            tr(
                f"You are currently in project directory '{resolved.name}' ({resolved}). Set up Multi-Agent team for this directory?",
                f"Bạn đang đứng tại thư mục project '{resolved.name}' ({resolved}). Bạn có muốn thiết lập Multi-Agent cho thư mục này không?",
            ),
            default=not is_self_repo,
        )
        if use_current:
            return resolved
        print(
            c(
                tr(
                    f"\n📂 Select a Project/Repo in {projects_root} to configure:",
                    f"\n📂 Hãy chọn Project/Repo trong {projects_root} muốn thiết lập đội AI:",
                ),
                BOLD + YELLOW,
            )
        )
    else:
        print(
            c(
                tr(
                    f"\n📂 You are in the root {projects_root} directory. Select a Project/Repo to configure:",
                    f"\n📂 Bạn đang ở thư mục gốc {projects_root}. Hãy chọn Project/Repo muốn thiết lập đội AI:",
                ),
                BOLD + YELLOW,
            )
        )

    if projects_root.exists() and projects_root.is_dir():
        subdirs = sorted(
            [
                d
                for d in projects_root.iterdir()
                if d.is_dir() and not d.name.startswith(".") and d.name != "agent-team"
            ],
            key=lambda p: p.name.lower(),
        )
        options: List[Tuple[str, str]] = []
        for d in subdirs:
            status_parts = []
            if (d / "AGENTS.md").exists():
                status_parts.append("AGENTS.md")
            if (d / ".agents" / "agents.json").exists():
                status_parts.append(".agents")
            if (d / ".codex" / "config.toml").exists():
                status_parts.append(".codex")
            badge = (
                tr(f"✓ Configured: {', '.join(status_parts)}", f"✓ Đã có: {', '.join(status_parts)}")
                if status_parts
                else tr("Not configured", "Chưa cài")
            )
            stack = detect_tech_stack(d)
            options.append((d.name, f"{stack} ({badge})"))
        new_proj_key = tr("[Create new Project folder]", "[Tạo thư mục Project mới]")
        root_proj_key = tr("[Configure at ~/Projects root]", "[Thiết lập ngay tại ~/Projects]")
        options.append((new_proj_key, tr("Create a new repository folder in ~/Projects", "Tạo một repo mới trong ~/Projects")))
        options.append((root_proj_key, tr("Create global configuration in ~/Projects", "Tạo cấu hình cấp toàn cục cho ~/Projects")))

        choice = ask_choice(tr("Select target Project/Repo", "Chọn Project/Repo đích"), options, default_index=0)
        if choice == root_proj_key:
            return projects_root
        if choice == new_proj_key:
            new_name = ask_text(
                tr("Enter new project folder name (in ~/Projects)", "Nhập tên thư mục project mới (trong ~/Projects)"),
                "my-new-project",
            )
            target = (projects_root / new_name).expanduser().resolve()
            target.mkdir(parents=True, exist_ok=True)
            return target
        return (projects_root / choice).resolve()
    return resolved


def ask_fallback_chain(role_id: str, default_chain: List[str]) -> List[str]:
    """Interactive builder for an agent's ordered cross-provider fallback chain."""
    default_str = format_fallback_chain(default_chain)
    presets = get_fallback_presets()
    mode_opts: List[Tuple[str, str]] = [
        (
            "keep",
            tr(
                f"Keep current fallback chain: {default_str}",
                f"Giữ chuỗi fallback hiện tại: {default_str}",
            ),
        ),
    ]
    for p_key, p_desc, _ in presets:
        mode_opts.append((f"preset:{p_key}", p_desc))
    mode_opts.extend(
        [
            (
                "custom-pick",
                tr(
                    "Build custom ordered chain step-by-step from Cross-Provider Catalog (agy / codex / claude)",
                    "Tự chọn thứ tự lùi model từng bước từ danh mục đa Provider (agy / codex / claude)",
                ),
            ),
            (
                "custom-text",
                tr(
                    "Type custom fallback chain manually (comma or '->' separated)",
                    "Tự nhập chuỗi fallback thủ công (cách nhau bằng dấu phẩy hoặc '->')",
                ),
            ),
        ]
    )

    choice = ask_choice(
        tr(
            f"[{role_id}] Configure Model & Cross-Provider Fallback Chain",
            f"[{role_id}] Thiết lập chuỗi lùi Model & Provider dự phòng (Fallback Chain)",
        ),
        mode_opts,
        default_index=0,
    )
    if choice == "keep":
        return list(default_chain)
    if choice.startswith("preset:"):
        p_id = choice.split(":", 1)[1]
        for k, _, ch in presets:
            if k == p_id:
                return list(ch)
    if choice == "custom-pick":
        catalog = get_cross_provider_fallback_catalog()
        print(
            f"\n{c('?', BOLD + GREEN)} {BOLD}"
            + tr(
                f"[{role_id}] Select fallback order (1st = Primary, 2nd = Fallback #1, 3rd = Fallback #2, ...):",
                f"[{role_id}] Chọn thứ tự ưu tiên lùi dần (số đầu = Model chính, tiếp theo = Dự phòng 1, 2, ...):",
            )
            + f"{RESET}"
        )
        for idx, (step_id, desc) in enumerate(catalog, start=1):
            print(f"  {c(str(idx), BOLD + CYAN)}. {BOLD}{step_id}{RESET} — {desc}")
        raw_order = ask_text(
            tr(
                "Enter ordered numbers separated by commas (e.g. 1,2,4,7)",
                "Nhập dãy số theo đúng thứ tự lùi dần, cách nhau dấu phẩy (VD: 1,2,4,7)",
            ),
            "1,2,4,7",
        )
        picked: List[str] = []
        for part in raw_order.split(","):
            part = part.strip()
            if part.isdigit():
                i = int(part) - 1
                if 0 <= i < len(catalog):
                    val = catalog[i][0]
                    if val not in picked:
                        picked.append(val)
            elif part and part not in picked:
                picked.append(part)
        return picked if picked else list(default_chain)

    raw_manual = ask_text(
        tr(
            f"[{role_id}] Enter fallback chain (e.g. agy:gemini-4-argon-high, agy:claude-opus-5-5-medium, agy:gemini-3.8-flash-high, codex:gpt-6.1-sol (xhigh))",
            f"[{role_id}] Nhập chuỗi fallback (VD: agy:gemini-4-argon-high, agy:claude-opus-5-5-medium, agy:gemini-3.8-flash-high, codex:gpt-6.1-sol (xhigh))",
        ),
        ", ".join(default_chain),
    )
    normalized = raw_manual.replace("->", ",").replace("→", ",")
    parsed = [s.strip() for s in normalized.split(",") if s.strip()]
    return parsed if parsed else list(default_chain)


def configure_single_agent(role_id: str, template: Dict, customize_deeply: bool) -> AgentSpec:
    print(
        c(
            tr(
                f"\n─── Configure Agent: [{role_id.upper()}] ({template['role']}) ───",
                f"\n─── Thiết lập Agent: [{role_id.upper()}] ({template['role']}) ───",
            ),
            BOLD + MAGENTA,
        )
    )
    default_chain: List[str] = list(
        template.get(
            "fallback_chain",
            [
                f"agy:{template['agy_model']}",
                f"claude:{template['claude_model']}",
                f"codex:{template['codex_model']} ({template['reasoning_effort']})",
            ],
        )
    )
    if not customize_deeply:
        print(f"  • {tr('Mission       ', 'Nhiệm vụ       ')}: {template['mission'][:95]}...")
        print(
            f"  • {tr('Primary Models', 'Model chính    ')}: Agy={c(template['agy_model'], CYAN)} | Codex={c(template['codex_model'], CYAN)} ({template['reasoning_effort']}) | Claude={c(template['claude_model'], CYAN)}"
        )
        print(
            f"  • {tr('Fallback Chain', 'Chuỗi Fallback ')}: {c(format_fallback_chain(default_chain), YELLOW)}"
        )
        print(f"  • {tr('Skills        ', 'Skills         ')}: {', '.join(template['skills'])}")
        if not ask_yes_no(
            tr(f"Customize details or fallback chain for agent '{role_id}'?", f"Bạn có muốn chỉnh sửa chi tiết hoặc chuỗi fallback cho agent '{role_id}' không?"),
            default=False,
        ):
            return AgentSpec(
                id=role_id,
                title=template["title"],
                role=template["role"],
                mission=template["mission"],
                provider=template["provider"],
                agy_model=template["agy_model"],
                claude_model=template["claude_model"],
                codex_model=template["codex_model"],
                reasoning_effort=template["reasoning_effort"],
                context_scope=template["context_scope"],
                goal_criteria=template["goal_criteria"],
                enable_write=bool(template["enable_write"]),
                enable_subagents=bool(template["enable_subagents"]),
                enable_mcp=bool(template["enable_mcp"]),
                workspace_mode=str(template["workspace_mode"]),
                agy_tools=list(template["agy_tools"]),
                skills=list(template["skills"]),
                fallback_chain=default_chain,
            )

    role_label = ask_text(tr(f"[{role_id}] Role title", f"[{role_id}] Tên vai trò (Role)"), template["role"])
    title = ask_text(tr(f"[{role_id}] Short description header", f"[{role_id}] Tiêu đề ngắn (Description header)"), template["title"])
    mission = ask_text(tr(f"[{role_id}] Specific mission", f"[{role_id}] Nhiệm vụ cụ thể (Mission)"), template["mission"])

    agy_choices = get_agy_model_choices()
    default_agy_idx = next(
        (i for i, (k, _) in enumerate(agy_choices) if k == template["agy_model"]),
        0,
    )
    agy_opts = list(agy_choices) + [("custom", tr("Enter a custom model name for Antigravity", "Tự nhập tên model bất kỳ cho Antigravity"))]
    agy_model = ask_choice(
        tr(f"[{role_id}] Select Model for Antigravity (agy)", f"[{role_id}] Chọn Model cho Antigravity (agy)"),
        agy_opts,
        default_index=default_agy_idx,
    )
    if agy_model == "custom":
        agy_model = ask_text(tr(f"[{role_id}] Enter Antigravity model name", f"[{role_id}] Nhập tên model Antigravity"), template["agy_model"])

    codex_choices = get_codex_model_choices()
    codex_opts = [(k, f"{desc}") for k, _, desc in codex_choices] + [
        ("custom", tr("Enter a custom model name for OpenAI Codex", "Tự nhập tên model bất kỳ cho OpenAI Codex"))
    ]
    default_codex_idx = next(
        (i for i, (k, _, _) in enumerate(codex_choices) if k == template["codex_model"]),
        0,
    )
    codex_choice = ask_choice(
        tr(f"[{role_id}] Select Model for OpenAI Codex (.codex)", f"[{role_id}] Chọn Model cho OpenAI Codex (.codex)"),
        codex_opts,
        default_index=default_codex_idx,
    )
    if codex_choice == "custom":
        codex_model = ask_text(tr(f"[{role_id}] Enter Codex model name", f"[{role_id}] Nhập tên model Codex"), template["codex_model"])
        reasoning_effort = ask_choice(
            tr(f"[{role_id}] Reasoning effort (model_reasoning_effort)", f"[{role_id}] Mức độ suy luận (model_reasoning_effort)"),
            [
                ("xhigh", tr("Extra High (xhigh)", "Cực cao (xhigh)")),
                ("high", tr("High (high)", "Cao (high)")),
                ("medium", tr("Medium (medium)", "Trung bình (medium)")),
                ("low", tr("Low/Fast (low)", "Thấp/Nhanh (low)")),
            ],
            default_index=1,
        )
    else:
        matched = next((item for item in codex_choices if item[0] == codex_choice), None)
        if matched:
            codex_model = "gpt-6-luna" if matched[0] == "gpt-6-luna-low" else matched[0]
            reasoning_effort = matched[1]
        else:
            codex_model = codex_choice
            reasoning_effort = template["reasoning_effort"]

    claude_choices = get_claude_model_choices()
    default_claude_idx = next(
        (i for i, (k, _) in enumerate(claude_choices) if k == template["claude_model"]),
        0,
    )
    claude_opts = list(claude_choices) + [("custom", tr("Enter a custom model name for Claude Code", "Tự nhập tên model cho Claude Code"))]
    claude_model = ask_choice(
        tr(f"[{role_id}] Select Model for Claude Code (.claude)", f"[{role_id}] Chọn Model cho Claude Code (.claude)"),
        claude_opts,
        default_index=default_claude_idx,
    )
    if claude_model == "custom":
        claude_model = ask_text(tr(f"[{role_id}] Enter Claude model name", f"[{role_id}] Nhập tên model Claude"), template["claude_model"])

    if default_chain and default_chain[0].startswith("agy:"):
        default_chain[0] = f"agy:{agy_model}"
    fallback_chain = ask_fallback_chain(role_id, default_chain)

    context_scope = ask_text(
        tr(f"[{role_id}] Context & Scope", f"[{role_id}] Ngữ cảnh & Phạm vi (Context/Scope)"),
        template["context_scope"],
    )
    goal_criteria = ask_text(
        tr(f"[{role_id}] Goal & Completion Criteria", f"[{role_id}] Mục tiêu & Tiêu chí hoàn thành (Goal/Completion Criteria)"),
        template["goal_criteria"],
    )

    enable_write = ask_yes_no(
        tr(f"[{role_id}] Grant file write & command execution permissions?", f"[{role_id}] Cấp quyền ghi/sửa file mã nguồn (Write tools)?"),
        default=bool(template["enable_write"]),
    )
    enable_subagents = ask_yes_no(
        tr(f"[{role_id}] Allow dispatching nested subagents?", f"[{role_id}] Cho phép gọi subagents con?"),
        default=bool(template["enable_subagents"]),
    )
    workspace_mode = "share" if enable_write and role_id != "orchestrator" else "inherit"
    agy_tools = list(READ_WRITE_TOOLS) if enable_write else list(template.get("agy_tools", REVIEWER_TOOLS))

    skills_raw = ask_text(
        tr(f"[{role_id}] Preferred skills for this agent", f"[{role_id}] Skills gắn riêng cho agent này"),
        ", ".join(template["skills"]),
    )
    agent_skills = [s.strip() for s in skills_raw.split(",") if s.strip()]

    return AgentSpec(
        id=role_id,
        title=title,
        role=role_label,
        mission=mission,
        provider="multi",
        agy_model=agy_model,
        claude_model=claude_model,
        codex_model=codex_model,
        reasoning_effort=reasoning_effort,
        context_scope=context_scope,
        goal_criteria=goal_criteria,
        enable_write=enable_write,
        enable_subagents=enable_subagents,
        enable_mcp=True,
        workspace_mode=workspace_mode,
        agy_tools=agy_tools,
        skills=agent_skills,
        fallback_chain=fallback_chain,
    )


def run_interactive_wizard(target_dir: Path, projects_root: Path, show_banner: bool = True) -> TeamConfig:
    if show_banner:
        banner()
    project_path = select_project_directory(target_dir, projects_root)
    project_name = project_path.name
    detected_stack = detect_tech_stack(project_path)

    existing_cfg_path = project_path / ".agents" / "team-config.json"
    existing_data: Optional[Dict] = None
    if existing_cfg_path.exists():
        try:
            existing_data = json.loads(existing_cfg_path.read_text(encoding="utf-8"))
            print(
                c(
                    tr(
                        f"\nℹ️ Found existing AI team config in {project_name} (updated: {existing_data.get('updated_at', '')}).",
                        f"\nℹ️ Phát hiện cấu hình đội AI đã có trong {project_name} (cập nhật: {existing_data.get('updated_at', '')}).",
                    ),
                    YELLOW,
                )
            )
        except Exception:
            existing_data = None

    print(
        c(
            tr(
                f"\n═══ STEP 1: PROJECT CONTEXT & PRIMARY GOAL [{project_name}] ═══",
                f"\n═══ BƯỚC 1: NGỮ CẢNH & MỤC TIÊU CỦA PROJECT [{project_name}] ═══",
            ),
            BOLD + BLUE,
        )
    )
    tech_stack = ask_text(
        tr("Project Tech Stack / Languages", "Tech Stack / Ngôn ngữ của Project"),
        existing_data.get("tech_stack", detected_stack) if existing_data else detected_stack,
    )
    stored_ctx = existing_data.get("project_context", "") if existing_data else ""
    default_ctx = (
        stored_ctx
        if _matches_current_lang(stored_ctx)
        else tr(
            f"{project_name} ({tech_stack}). Keep changes small and complete, prioritize TDD and independent code review.",
            f"Dự án {project_name} ({tech_stack}). Giữ thay đổi nhỏ gọn, ưu tiên TDD và kiểm định độc lập.",
        )
    )
    project_context = ask_text(
        tr("Project Context (architecture, conventions, notes)", "Ngữ cảnh chung của Project (kiến trúc, quy ước, lưu ý)"),
        default_ctx,
    )

    stored_goal = existing_data.get("project_goal", "") if existing_data else ""
    default_goal = (
        stored_goal
        if _matches_current_lang(stored_goal)
        else tr(
            f"Develop, test, and maintain {project_name} through a directly orchestrated Multi-Agent team.",
            f"Phát triển, kiểm thử và duy trì {project_name} thông qua đội ngũ Multi-Agent điều phối trực tiếp.",
        )
    )
    project_goal = ask_text(
        tr("Primary Project Goal", "Mục tiêu chính của Project hiện tại (Goal)"),
        default_goal,
    )

    rule_options = [
        (
            "graphify",
            tr(
                "Graphify Rule (Prefer `graphify query` before source reads if `graphify-out/graph.json` exists; run `graphify update .` after edits)",
                "Graphify Rule (Ưu tiên `graphify query` trước khi đọc source nếu có `graphify-out/graph.json`, chạy `graphify update .` sau khi sửa code)",
            ),
        ),
        (
            "drawio-erd",
            tr(
                "System Design / Draw.io Rule (Read `/home/killua/ryan/Study/System design/AGENTS.md` before creating/editing ERDs or `.drawio`)",
                "System Design / Draw.io Rule (Đọc `/home/killua/ryan/Study/System design/AGENTS.md` trước khi vẽ ERD/.drawio)",
            ),
        ),
        (
            "commit-restrictions",
            tr(
                "Git Commit Restrictions Rule (Create `.agents/rules/commit-restrictions.md` blocking commits of AGENTS.md / SKILL.md)",
                "Git Commit Restrictions Rule (Tạo `.agents/rules/commit-restrictions.md` chặn commit nhầm AGENTS.md / SKILL.md)",
            ),
        ),
    ]
    selected_extra_rules = ask_multi_choice(
        tr("Select Workspace Rules to include in this Project", "Chọn các Quy tắc Đặc thù muốn gắn vào Project này"),
        rule_options,
        default_indices=[0, 1],
    )
    custom_rule = ask_text(
        tr("Enter an optional custom project rule (or press Enter to skip)", "Nhập thêm quy tắc đặc thù riêng của dự án (hoặc nhấn Enter để bỏ qua)"),
        "",
    )
    if custom_rule.strip():
        selected_extra_rules.append(f"custom:{custom_rule.strip()}")

    harness_options = [
        (
            "agy",
            tr(
                "Google Antigravity — AGENTS.md, .agents/agents.json, .agents/agents/*/agent.md, .agents/skills.json",
                "Google Antigravity — AGENTS.md, .agents/agents.json, .agents/agents/*/agent.md, .agents/skills.json",
            ),
        ),
        (
            "codex",
            tr(
                "OpenAI Codex CLI — .codex/config.toml & .agents/agents/*/agent.toml",
                "OpenAI Codex CLI — .codex/config.toml & .agents/agents/*/agent.toml",
            ),
        ),
        (
            "claude",
            tr(
                "Anthropic Claude Code — CLAUDE.md & .claude/agents/*.md",
                "Anthropic Claude Code — CLAUDE.md & .claude/agents/*.md",
            ),
        ),
    ]
    harnesses = ask_multi_choice(
        tr("Select target harnesses to generate configs for", "Chọn các công cụ điều phối cần sinh cấu hình"),
        harness_options,
        default_indices=[0, 1, 2],
    )

    print(
        c(
            tr(
                "\n═══ STEP 2: AGENT ROSTER & ROLE CONFIGURATION ═══",
                "\n═══ BƯỚC 2: CHỌN ĐỘI HÌNH AGENTS & PHÂN CÔNG NHIỆM VỤ ═══",
            ),
            BOLD + BLUE,
        )
    )
    role_options = [
        (
            "lead-architect",
            tr(
                "Lead Solution Architect & Planner — Agy: gemini-4-argon-high | Codex: gpt-6-astra high",
                "Kiến trúc sư trưởng & Hoạch định giải pháp — Agy: gemini-4-argon-high | Codex: gpt-6-astra high",
            ),
        ),
        (
            "lead-critic",
            tr(
                "Lead Technical Critic & Challenger — Agy: gemini-3.1-pro-high | Codex: gpt-6.1-sol xhigh",
                "Phản biện trưởng & Thẩm định rủi ro — Agy: gemini-3.1-pro-high | Codex: gpt-6.1-sol xhigh",
            ),
        ),
        (
            "orchestrator",
            tr(
                "Lead Execution Orchestrator — Agy: gemini-4-argon-high | Codex: gpt-6-astra high",
                "Tổng điều phối viên thực thi — Agy: gemini-4-argon-high | Codex: gpt-6-astra high",
            ),
        ),
        (
            "reviewer",
            tr(
                "Independent Read-Only Reviewer — Agy: gemini-3.1-pro-high | Codex: gpt-6.1-sol xhigh",
                "Kiểm định viên độc lập (Read-Only) — Agy: gemini-3.1-pro-high | Codex: gpt-6.1-sol xhigh",
            ),
        ),
        (
            "designer",
            tr(
                "UI/UX & Anti-Slop Visual Designer — Agy: gemini-3.8-flash-high | Codex: gpt-6-sol xhigh",
                "Kỹ sư thiết kế UI/UX & Bản sắc thị giác — Agy: gemini-3.8-flash-high | Codex: gpt-6-sol xhigh",
            ),
        ),
        (
            "implementer",
            tr(
                "Feature & TDD Implementer — Agy: gemini-3.8-flash-high | Codex: gpt-6-sol xhigh",
                "Kỹ sư thực thi tính năng & TDD — Agy: gemini-3.8-flash-high | Codex: gpt-6-sol xhigh",
            ),
        ),
        (
            "searcher",
            tr(
                "Documentation & Codebase Scout — Agy: gemini-3.8-flash-medium | Codex: gpt-6-luna medium",
                "Trinh sát mã nguồn & Tài liệu — Agy: gemini-3.8-flash-medium | Codex: gpt-6-luna medium",
            ),
        ),
        (
            "committer",
            tr(
                "Conventional Git Committer — Agy: gemini-3.7-flash | Codex: gpt-6-luna low",
                "Chuyên viên đóng gói Git Commit — Agy: gemini-3.7-flash | Codex: gpt-6-luna low",
            ),
        ),
    ]
    selected_roles = ask_multi_choice(
        tr("Select Agents to include in this Project's roster", "Chọn các Agents trong đội hình của Project này"),
        role_options,
        default_indices=[0, 1, 2, 3, 4, 5, 6, 7],
    )

    active_templates = get_agent_templates()
    while ask_yes_no(
        tr(
            "Add a custom specialist Agent (e.g. security-auditor, ml-tuner, devops-infra)?",
            "Bạn có muốn thêm một Agent chuyên biệt mới (VD: security-auditor, ml-tuner, devops-infra)?",
        ),
        default=False,
    ):
        custom_id = ask_text(
            tr("Enter ID for the new agent (lowercase, hyphenated)", "Nhập ID cho agent mới (viết thường, nối bằng dấu gạch ngang)"),
            "custom-specialist",
        )
        custom_id = re.sub(r"[^a-z0-9_-]", "-", custom_id.lower()).strip("-") or "custom-agent"
        if custom_id not in active_templates:
            active_templates[custom_id] = {
                "title": tr(
                    f"Specialized {custom_id.replace('-', ' ').title()} Agent",
                    f"Agent chuyên biệt {custom_id.replace('-', ' ').title()}",
                ),
                "role": tr(f"Specialist — {custom_id}", f"Chuyên gia — {custom_id}"),
                "mission": tr(
                    f"Execute specialized {custom_id} tasks delegated by the Orchestrator.",
                    f"Thực thi các tác vụ chuyên biệt {custom_id} do Orchestrator phân công.",
                ),
                "provider": "multi",
                "agy_model": "gemini-3.8-flash-high",
                "claude_model": "sonnet",
                "codex_model": "gpt-6-sol",
                "reasoning_effort": "high",
                "context_scope": tr(
                    f"Modules and documentation related to {custom_id}.",
                    f"Các module và tài liệu liên quan tới {custom_id}.",
                ),
                "goal_criteria": tr(
                    f"Complete assigned {custom_id} tasks with verifiable output.",
                    f"Hoàn thành tác vụ {custom_id} được giao với kết quả kiểm chứng được.",
                ),
                "enable_write": True,
                "enable_subagents": False,
                "enable_mcp": True,
                "workspace_mode": "share",
                "agy_tools": list(READ_WRITE_TOOLS),
                "skills": [],
                "fallback_chain": [
                    "agy:gemini-3.8-flash-high",
                    "agy:gemini-3.1-pro-high",
                    "claude:sonnet",
                    "codex:gpt-6-sol (xhigh)",
                ],
            }
        if custom_id not in selected_roles:
            selected_roles.append(custom_id)

    setup_mode_options = [
        (
            "guided",
            tr(
                "Step through each Agent with detailed prompts (Mission, Model, Fallback Chain, Context, Goal)",
                "Đi qua từng Agent để đặt câu hỏi chi tiết (Nhiệm vụ, Model, Chuỗi Fallback, Ngữ cảnh, Mục tiêu)",
            ),
        ),
        (
            "quick",
            tr(
                "Review standard summary per Agent and only customize specific ones",
                "Xem tóm tắt chuẩn cho từng Agent và chỉ chỉnh sửa Agent nào cần đổi",
            ),
        ),
    ]
    setup_mode = ask_choice(
        tr("Select Agent configuration mode", "Chọn chế độ thiết lập từng Agent"),
        setup_mode_options,
        default_index=0,
    )
    customize_deeply = setup_mode == "guided"

    agents: List[AgentSpec] = []
    for role_id in selected_roles:
        tpl = dict(active_templates[role_id])
        if existing_data and "agents" in existing_data:
            for old_ag in existing_data["agents"]:
                if old_ag.get("id") == role_id:
                    for k in ("agy_model", "claude_model", "codex_model", "reasoning_effort", "enable_write", "enable_subagents", "enable_mcp", "workspace_mode", "agy_tools", "skills", "fallback_chain"):
                        if k in old_ag and old_ag[k]:
                            tpl[k] = old_ag[k]
                    for text_key in ("title", "role", "mission", "context_scope", "goal_criteria"):
                        val = str(old_ag.get(text_key, ""))
                        if _matches_current_lang(val):
                            tpl[text_key] = val
        spec = configure_single_agent(role_id, tpl, customize_deeply)
        agents.append(spec)

    print(
        c(
            tr(
                "\n═══ STEP 3: SELECT & APPLY WORKSPACE SKILLS ═══",
                "\n═══ BƯỚC 3: CHỌN & APPLY SKILLS VÀO PROJECT / REPO ═══",
            ),
            BOLD + BLUE,
        )
    )
    discovered_skills = discover_local_skills()
    print(
        tr(
            f"Discovered {c(str(len(discovered_skills)), BOLD + GREEN)} local skills across `~/.gemini/config/plugins`, `Hephaestus/.agents/skills`, and `builtin`.",
            f"Đã quét thấy {c(str(len(discovered_skills)), BOLD + GREEN)} skills từ `~/.gemini/config/plugins`, `Hephaestus/.agents/skills`, và `builtin`.",
        )
    )
    bundle_keys = list(SKILL_BUNDLES.keys())
    label_key = "label_vi" if CURRENT_LANG == "vi" else "label_en"
    desc_key = "description_vi" if CURRENT_LANG == "vi" else "description_en"
    bundle_opts = [(k, f"{SKILL_BUNDLES[k][label_key]} — {SKILL_BUNDLES[k][desc_key]}") for k in bundle_keys]
    chosen_bundles = ask_multi_choice(
        tr("Select Skill Bundles to apply to this Project", "Chọn các Gói Kỹ năng muốn apply cho Project này"),
        bundle_opts,
        default_indices=[0, 1, 4],
    )

    skill_names_set = set()
    for b_key in chosen_bundles:
        for s_name in SKILL_BUNDLES[b_key]["skills"]:  # type: ignore[index]
            skill_names_set.add(s_name)
    for ag in agents:
        for s_name in ag.skills:
            skill_names_set.add(s_name)

    extra_skills_raw = ask_text(
        tr(
            "Enter additional skill names to attach, or press Enter to skip",
            "Nhập thêm tên các skills lẻ muốn gắn thêm, hoặc nhấn Enter để bỏ qua",
        ),
        "",
    )
    if extra_skills_raw.strip():
        for s in extra_skills_raw.split(","):
            if s.strip():
                skill_names_set.add(s.strip())

    apply_mode_opts = [
        (
            "symlink",
            tr(
                "Register `.agents/skills.json` + Create symlinks in `.agents/skills/`",
                "Khai báo `.agents/skills.json` + Tạo symlink trực tiếp vào `.agents/skills/`",
            ),
        ),
        (
            "copy",
            tr(
                "Register `.agents/skills.json` + Copy full skill folders into `.agents/skills/`",
                "Khai báo `.agents/skills.json` + Copy toàn bộ thư mục skill vào `.agents/skills/`",
            ),
        ),
        (
            "json-only",
            tr(
                "Only register paths in `.agents/skills.json`",
                "Chỉ khai báo đường dẫn trong `.agents/skills.json`",
            ),
        ),
    ]
    skill_apply_mode = ask_choice(
        tr("Select Skill application mode", "Cách thức Apply Skills vào Project"),
        apply_mode_opts,
        default_index=0,
    )

    resolved_skills: List[Dict[str, str]] = []
    for s_name in sorted(skill_names_set):
        if s_name in discovered_skills:
            resolved_skills.append(discovered_skills[s_name])

    return TeamConfig(
        project_name=project_name,
        project_path=str(project_path),
        tech_stack=tech_stack,
        project_context=project_context,
        project_goal=project_goal,
        extra_rules=selected_extra_rules,
        harnesses=harnesses,
        skill_apply_mode=skill_apply_mode,
        add_commit_restrictions=("commit-restrictions" in selected_extra_rules),
        selected_skill_bundles=chosen_bundles,
        selected_skills=resolved_skills,
        agents=agents,
        updated_at=datetime.now().isoformat(timespec="seconds"),
    )


# ---------------------------------------------------------------------------
# Generators: Chuẩn Orpheus / Act2Morse / Hephaestus + Antigravity + Codex + Claude
# ---------------------------------------------------------------------------
def format_extra_rules_bullets(cfg: TeamConfig) -> List[str]:
    bullets: List[str] = []
    for r in cfg.extra_rules:
        if r == "graphify":
            bullets.extend(
                [
                    "- For `/graphify`, use the installed Graphify skill or instructions first.",
                    "- When `graphify-out/graph.json` exists, run `graphify query \"<question>\"` before source searches or reads. Read only lines located by the graph or earlier reads. Include this rule in every subagent prompt exploring code.",
                    "- Use `graphify path \"<A>\" \"<B>\"` for relationships and `graphify explain \"<concept>\"` for focused concepts. After code changes, run `graphify update .`; whole-file graph rewrites are expected, not churn.",
                ]
            )
        elif r == "drawio-erd":
            bullets.append(
                "- Before creating or editing ERDs or `.drawio` files, read `/home/killua/ryan/Study/System design/AGENTS.md` for layout, palette, connector, and Google Drive workflow rules."
            )
        elif r.startswith("custom:"):
            bullets.append(f"- {r[len('custom:'):]}")
    return bullets


MAX_AGENTS_MD_LINES = 148


def enforce_agents_md_line_limit(content: str, max_lines: int = MAX_AGENTS_MD_LINES) -> str:
    """Đảm bảo AGENTS.md luôn dưới 150 dòng (< 150 lines). Phần chi tiết được đẩy sang .agents/README.md."""
    lines = content.splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines) + "\n"
    kept = lines[: max_lines - 2]
    kept.append("")
    kept.append("- *(Truncated to stay < 150 lines — see `.agents/README.md` for full details)*")
    return "\n".join(kept) + "\n"


def _parse_markdown_h2_sections(content: str) -> Tuple[str, List[Tuple[str, List[str]]]]:
    """
    Parse a markdown document into preamble and level-2 sections (## ...).
    Does NOT split on level-3 subheadings (### ...).
    Returns (preamble, [(heading_line, section_lines), ...]).
    """
    lines = content.splitlines()
    preamble_lines: List[str] = []
    sections: List[Tuple[str, List[str]]] = []
    current_heading: Optional[str] = None
    current_body: List[str] = []

    for line in lines:
        if line.startswith("## "):
            if current_heading is not None:
                sections.append((current_heading, current_body))
            current_heading = line.strip()
            current_body = [line]
        elif current_heading is not None:
            current_body.append(line)
        else:
            preamble_lines.append(line)

    if current_heading is not None:
        sections.append((current_heading, current_body))

    preamble = "\n".join(preamble_lines).strip()
    return preamble, sections


def build_root_agents_md(cfg: TeamConfig, existing_content: Optional[str] = None) -> str:
    """
    Sinh hoặc cập nhật AGENTS.md tại gốc repo theo đúng chuẩn Orpheus / Act2Morse (< 150 lines):
    - Nếu repo đã có sẵn AGENTS.md với các mục riêng (như Project Structure, Build Commands...),
      giữ nguyên phần hướng dẫn riêng của repo và cập nhật các mục do `agt` quản lý:
      `## Team Topology & Delegation Rules` và `## Agent-Specific Instructions`!
    """
    subagent_lines = [
        "- Workspace subagents are located in `.agents/agents/{agent_name}/agent.md` (and configured for Codex in `.agents/agents/{agent_name}/agent.toml` via `.codex/config.toml`):"
    ]
    for ag in cfg.agents:
        chain_note = f", Fallback: `{format_fallback_chain(ag.fallback_chain)}`" if ag.fallback_chain else ""
        subagent_lines.append(
            f"  - `{ag.id}`: `.agents/agents/{ag.id}/agent.md` "
            f"(Agy: `{ag.agy_model}`, Codex: `{ag.codex_model}` {ag.reasoning_effort}{chain_note}) — {ag.role}"
        )

    extra_bullets = format_extra_rules_bullets(cfg)
    skills_summary = ", ".join(f"`{s['name']}`" for s in cfg.selected_skills)

    contract_bullet = tr(
        "- **Execution & Concurrency Contract**: Keep `agt` as a multi-harness scaffold and run via host-native orchestration (`agy`, `codex`, `claude`). Allow parallel fan-out for independent reads; keep shared-file edits (single-writer), independent verification, and commits strictly ordered. Consider a workflow graph only when the host must enforce hard gates, checkpoint/restore state, or run systematic retries (details in `.agents/README.md`).",
        "- **Execution & Concurrency Contract**: Giữ `agt` làm scaffold đa harness và chạy bằng orchestration native của host (`agy`, `codex`, `claude`). Cho phép fan-out các việc đọc độc lập; giữ sửa file chung (single-writer), kiểm định độc lập và commit theo đúng thứ tự tuần tự. Chỉ cân nhắc workflow graph khi host cần thực thi gate, lưu/khôi phục state hoặc retry có hệ thống (chi tiết tại `.agents/README.md`).",
    )

    agent_section_lines = [
        "## Agent-Specific Instructions",
        "",
        f"- **Project Context**: {cfg.project_context}",
        f"- **Primary Goal**: {cfg.project_goal}",
        "- **Line Limit**: Keep `AGENTS.md` strictly under 150 lines; put detailed specs in `.agents/README.md`.",
        "- **Model & Cross-Provider Fallback**: When a primary model hits quota/rate limits, step down along the agent's `Fallback` chain (or run `agt fallback --step-down <role>`); if Antigravity models are exhausted, switch execution to the configured OpenAI Codex provider.",
        contract_bullet,
        *extra_bullets,
        *subagent_lines,
        f"- **Applied Workspace Skills**: {skills_summary or 'See `.agents/skills.json`'}.",
        "- Read `.agents/README.md` for the full role & model mapping table.",
    ]
    agent_section = "\n".join(agent_section_lines)

    topology_section = "\n".join(
        [
            tr("## Team Topology & Delegation Rules", "## Cấu Trúc Đội Ngũ & Quy Tắc Ủy Quyền"),
            "",
            tr(
                "### Phase 1: Bounded 2-Round Lead Debate (Strategy & Stress-Testing)",
                "### Phase 1: Bounded 2-Round Lead Debate (Chiến lược & Phản biện)",
            ),
            tr(
                "- `lead-architect`: Formulates initial architecture, design specs, and task breakdown.",
                "- `lead-architect`: Xây dựng đề xuất kiến trúc ban đầu, thông số thiết kế và phân rã task.",
            ),
            tr(
                "- `lead-critic`: Stress-tests assumptions, security, scalability, edge cases, and YAGNI simplicity across 2 structured debate rounds.",
                "- `lead-critic`: Phản biện độc lập, stress-test giả định, rủi ro bảo mật/hiệu năng và YAGNI trong đúng 2 vòng.",
            ),
            tr(
                "- Consensus (`CONSENSUS_REACHED`) is required before passing the blueprint to Phase 2.",
                "- Bắt buộc đạt đồng thuận (`CONSENSUS_REACHED`) trước khi chuyển giao kế hoạch sang Pha 2.",
            ),
            "",
            tr(
                "### Phase 2: Hierarchical Execution (Orchestrator + Sub-agents)",
                "### Phase 2: Hierarchical Execution (Điều phối & Thực thi phân cấp)",
            ),
            tr(
                "- `orchestrator`: Takes the approved blueprint and coordinates worker subagents without direct code edits.",
                "- `orchestrator`: Nhận thiết kế đã duyệt, tổng điều phối các worker subagents mà không sửa code trực tiếp.",
            ),
            tr(
                "- `searcher`: Read-only codebase scouting and documentation lookup to maintain clean context.",
                "- `searcher`: Trinh sát mã nguồn và tra cứu tài liệu ở chế độ chỉ đọc để giữ sạch context.",
            ),
            tr(
                "- `designer`: UI/UX & Anti-Slop visual styling adhering to design taste rules.",
                "- `designer`: Kỹ sư thiết kế UI/UX & bản sắc thị giác Anti-Slop tuân thủ design taste.",
            ),
            tr(
                "- `implementer`: Minimal TDD implementation (Red-Green-Refactor) with single-writer file boundaries.",
                "- `implementer`: Kỹ sư thực thi code & viết test theo quy trình TDD (Red-Green-Refactor) với thay đổi nhỏ nhất.",
            ),
            tr(
                "- `reviewer`: Independent 2-axis quality and security review (Spec & Coding Standards).",
                "- `reviewer`: Kiểm định độc lập chất lượng code và bảo mật theo 2 trục Spec & Coding Standards.",
            ),
            tr(
                "- `committer`: Atomic Conventional Commits after reviewer approval.",
                "- `committer`: Đóng gói Git Commit chuẩn Conventional Commits sau khi reviewer duyệt.",
            ),
        ]
    )

    if existing_content and existing_content.strip():
        preamble, parsed_sections = _parse_markdown_h2_sections(existing_content)
        managed_topology_headings = {
            "## Team Topology & Delegation Rules",
            "## Cấu Trúc Đội Ngũ & Quy Tắc Ủy Quyền",
        }
        managed_agent_headings = {
            "## Agent-Specific Instructions",
        }

        parts: List[str] = []
        if preamble:
            parts.append(preamble)

        topology_replaced = False
        agent_replaced = False

        for h, sec_lines in parsed_sections:
            if h in managed_topology_headings:
                if not topology_replaced:
                    parts.append(topology_section.strip())
                    topology_replaced = True
            elif h in managed_agent_headings:
                if not agent_replaced:
                    parts.append(agent_section.strip())
                    agent_replaced = True
            else:
                sec_text = "\n".join(sec_lines).strip()
                if sec_text:
                    parts.append(sec_text)

        if not topology_replaced:
            parts.append(topology_section.strip())
        if not agent_replaced:
            parts.append(agent_section.strip())

        combined = "\n\n".join(parts) + "\n"
        merged_lines = combined.splitlines()
        if len(merged_lines) > MAX_AGENTS_MD_LINES:
            raise ValueError(
                f"Merged AGENTS.md requires {len(merged_lines)} lines (max {MAX_AGENTS_MD_LINES} < 150). "
                "Move detailed documentation into .agents/README.md before regenerating."
            )
        return "\n".join(merged_lines) + "\n"

    fresh = "\n".join(
        [
            f"# Repository & Agent Guidelines — {cfg.project_name}",
            "",
            tr("## Project Context & Goals", "## Bối Cảnh & Mục Tiêu Dự Án"),
            "",
            f"- **Tech Stack**: {cfg.tech_stack}",
            f"- **Context**: {cfg.project_context}",
            f"- **Current Goal**: {cfg.project_goal}",
            "",
            topology_section,
            "",
            agent_section,
        ]
    )
    return enforce_agents_md_line_limit(fresh)


def build_agents_readme_md(cfg: TeamConfig) -> str:
    """Sinh file .agents/README.md theo đúng chuẩn Orpheus / Act2Morse."""
    rows = []
    for ag in cfg.agents:
        chain_str = format_fallback_chain(ag.fallback_chain)
        rows.append(
            f"| `{ag.id}` | `.agents/agents/{ag.id}/agent.md` | `{ag.agy_model}` | `{ag.codex_model}` ({ag.reasoning_effort}) | `{chain_str}` | {ag.role} — {ag.mission} |"
        )
    rows_block = "\n".join(rows)

    skill_rows = []
    for s in cfg.selected_skills:
        skill_rows.append(f"- **`{s['name']}`**: {s['description']}")
    skills_block = "\n".join(skill_rows) if skill_rows else "- None"

    header_title = tr(
        f"# {cfg.project_name} Agents & Skills",
        f"# Danh Mục Agents & Skills — {cfg.project_name}",
    )
    discovery_intro = tr(
        "Workspace subagents are located in `.agents/agents/{agent_name}/agent.md`.\n\n"
        "Both **Codex**, **Claude Code**, and **Antigravity CLI (`agy`)** discover the agents in this workspace natively:\n"
        "- **agy** reads `.agents/agents/{agent_name}/agent.md`, `.agents/agents.json`, and `.agents/skills.json`.\n"
        "- **Codex** reads `.agents/agents/{agent_name}/agent.toml` registered via `.codex/config.toml`.\n"
        "- **Claude Code** reads `.claude/agents/{agent_name}.md` and `CLAUDE.md`.",
        "Các subagents được cấu hình tại `.agents/agents/{agent_name}/agent.md`.\n\n"
        "Cả 3 harness (**Antigravity CLI `agy`**, **Codex**, và **Claude Code**) phát hiện agent theo cơ chế native:\n"
        "- **agy** đọc `.agents/agents/{agent_name}/agent.md`, `.agents/agents.json`, và `.agents/skills.json`.\n"
        "- **Codex** đọc `.agents/agents/{agent_name}/agent.toml` được đăng ký qua `.codex/config.toml`.\n"
        "- **Claude Code** đọc `.claude/agents/{agent_name}.md` và `CLAUDE.md`.",
    )
    roles_heading = tr("## Agent Roles & Model Mapping", "## Bảng Vai Trò & Ánh Xạ Mô Hình")
    table_header = tr(
        "| Role | Workspace Path | Model (Agy) | Model (Codex) | Fallback Chain | Purpose |\n| --- | --- | --- | --- | --- | --- |",
        "| Vai trò | Đường dẫn Workspace | Mô hình (Agy) | Mô hình (Codex) | Fallback Chain | Mục tiêu |\n| --- | --- | --- | --- | --- | --- |",
    )
    context_heading = tr("## Project Context & Goal", "## Bối Cảnh & Mục Tiêu Dự Án")
    context_label = tr("Context", "Bối cảnh")
    goal_label = tr("Goal", "Mục tiêu")
    skills_heading = tr("## Applied Skills", "## Kỹ Năng Áp Dụng")

    native_section = tr(
        "## Host-Native Orchestration (Zero Custom Runtime)\n\n"
        "`agent-team` (`agt`) operates strictly as a multi-harness scaffold and generator. It avoids adding custom runtime daemons or process emulators to simulate agents:\n"
        "- **Antigravity (`agy`)**: Orchestration is driven via host-native `invoke_subagent` and `send_message` tools using definitions in `.agents/agents/`.\n"
        "- **OpenAI Codex (`codex`)**: Uses native multi-agent thread dispatch enabled via `[agents]` configurations in `.codex/config.toml`.\n"
        "- **Claude Code (`claude`)**: Orchestrates via subagent markdown profiles in `.claude/agents/` referenced through `CLAUDE.md`.",
        "## Host-Native Orchestration (Zero Custom Runtime)\n\n"
        "`agent-team` (`agt`) thuần túy là bộ scaffold và generator đa harness. Dự án không tạo runtime daemon hay process giả lập agent riêng:\n"
        "- **Antigravity (`agy`)**: Điều phối thông qua các công cụ native của host như `invoke_subagent` và `send_message` theo khai báo tại `.agents/agents/`.\n"
        "- **OpenAI Codex (`codex`)**: Tận dụng cơ chế luồng native đa agent kích hoạt bởi `[agents]` trong `.codex/config.toml`.\n"
        "- **Claude Code (`claude`)**: Điều phối qua hồ sơ subagent markdown tại `.claude/agents/` kết nối với `CLAUDE.md`.",
    )

    concurrency_section = tr(
        "## Execution Concurrency & Ordering Contract\n\n"
        "To balance execution throughput and correctness, all dispatches must follow these ordering principles:\n"
        "1. **Parallel Read Fan-Out**: Independent codebase scouting and documentation search tasks (`searcher`) can fan out in parallel to maximize discovery speed.\n"
        "2. **Ordered Shared-File Edits (Single-Writer)**: Implementation tasks (`implementer`, `designer`) that touch overlapping files or shared module contracts must execute sequentially with strict single-writer boundaries.\n"
        "3. **Ordered Verification & Commit**: Once implementation passes local unit tests, `reviewer` performs an independent 2-axis quality and security review. Only after `reviewer` grants `APPROVED`, `committer` packages atomic Conventional Commits.",
        "## Giao Thức Đồng Thời & Thứ Tự Thực Thi (Concurrency & Ordering Contract)\n\n"
        "Để đảm bảo tốc độ và tính toàn vẹn của mã nguồn, mọi điều phối phải tuân thủ các quy tắc thứ tự:\n"
        "1. **Parallel Read Fan-Out**: Các tác vụ trinh sát mã nguồn và tra cứu tài liệu độc lập (`searcher`) có thể chạy song song (fan-out) để tối đa tốc độ khám phá.\n"
        "2. **Ordered Shared-File Edits (Single-Writer)**: Tác vụ triển khai code (`implementer`, `designer`) khi chạm vào các tệp dùng chung hoặc hợp đồng module phải thực thi tuần tự theo nguyên tắc đơn ghi (single-writer).\n"
        "3. **Ordered Verification & Commit**: Sau khi code hoàn thành và test cục bộ pass, `reviewer` thực hiện kiểm định độc lập 2 trục. Chỉ khi `reviewer` duyệt `APPROVED`, `committer` mới đóng gói atomic Conventional Commit.",
    )

    boundary_section = tr(
        "## Workflow Graph Decision Boundary\n\n"
        "A graph-based state machine or formal workflow orchestrator is NOT required for standard linear development. Consider introducing an external workflow graph only when the target environment demands:\n"
        "- **Gate Enforcement**: Enforcing programmatic host quality gates that strictly prevent progression before formal sign-off.\n"
        "- **State Checkpointing & Resumption**: Checkpointing execution state to disk so long-running multi-step operations can pause, survive host restarts, and resume gracefully.\n"
        "- **Systematic Retry Loops**: Managing automated remediation cycles where failed review or verification steps automatically re-dispatch targeted worker prompts.\n\n"
        "Do not introduce a custom runtime or graph engine merely to represent role hierarchy.",
        "## Ranh Giới Quyết Định Workflow Graph (Workflow Graph Decision Boundary)\n\n"
        "Mô hình máy trạng thái dạng đồ thị (workflow graph) không bắt buộc cho quy trình phát triển thông thường. Chỉ cân nhắc tích hợp workflow graph khi môi trường thực thi yêu cầu:\n"
        "- **Cổng Chặn (Gate Enforcement)**: Thực thi các cổng kiểm soát chất lượng có tính cưỡng chế của host, ngăn chặn chuyển pha khi chưa đủ điều kiện.\n"
        "- **Lưu/Khôi Phục State (State Checkpointing & Resumption)**: Lưu checkpoint trạng thái thực thi bền vững xuống đĩa để có thể tạm dừng, phục hồi sau khi khởi động lại host.\n"
        "- **Vòng Lặp Thử Lại Có Hệ Thống (Systematic Retry Loops)**: Quản lý chu trình tự động sửa lỗi và điều phối lại có hệ thống khi bước kiểm định hoặc review chưa đạt.\n\n"
        "Tuyệt đối không bổ sung custom runtime hay engine đồ thị chỉ để mô phỏng cấu trúc vai trò.",
    )

    return (
        f"{header_title}\n\n"
        f"{discovery_intro}\n\n"
        f"{roles_heading}\n\n"
        f"{table_header}\n"
        f"{rows_block}\n\n"
        f"{native_section}\n\n"
        f"{concurrency_section}\n\n"
        f"{boundary_section}\n\n"
        f"{context_heading}\n\n"
        f"- **{context_label}**: {cfg.project_context}\n"
        f"- **{goal_label}**: {cfg.project_goal}\n\n"
        f"{skills_heading}\n\n"
        f"{skills_block}\n"
    )


def _to_agy_model_tier(agy_model: str) -> str:
    """
    Map a descriptive model string (e.g. 'gemini-4-argon-high') to a valid
    Antigravity ModelTier enum ('pro', 'flash', 'flash_lite', 'inherit')
    required by agy's AgentFrontmatter loader.
    """
    raw = (agy_model or "").strip().lower()
    if raw in ("pro", "flash", "flash_lite", "inherit"):
        return raw
    if any(k in raw for k in ("argon", "pro", "opus", "ultra")):
        return "pro"
    if any(k in raw for k in ("lite", "3.7-flash", "haiku")):
        return "flash_lite"
    if any(k in raw for k in ("flash", "sonnet")):
        return "flash"
    return "inherit"


def build_agents_json(cfg: TeamConfig) -> Dict[str, List[Dict[str, str]]]:
    """Sinh file .agents/agents.json theo chuẩn customizations.JSONConfig của Antigravity."""
    return {
        "entries": [
            {
                "path": ".agents/agents",
            }
        ]
    }


def build_single_agent_md(cfg: TeamConfig, ag: AgentSpec) -> str:
    """
    Sinh file `.agents/agents/<role>/agent.md` theo đúng chuẩn YAML frontmatter của Antigravity:
    name, description, model (pro|flash|flash_lite|inherit), mainAgent, subagent, tools
    + `# Agent System Instructions`.
    """
    model_tier = _to_agy_model_tier(ag.agy_model)
    canonical_tools = canonicalize_antigravity_tools(ag.agy_tools, enable_write=ag.enable_write)
    tools_yaml = "\n".join(f"  - {t}" for t in canonical_tools)
    fallback_line = (
        f"\n- **Fallback Chain**: `{format_fallback_chain(ag.fallback_chain)}` "
        f"(If the active model hits quota/rate limits, step down in this exact order; if Antigravity quota is exhausted, switch/delegate to the OpenAI Codex provider profile)."
        if ag.fallback_chain
        else ""
    )
    graphify_line = (
        "\n- Follow AGENTS.md. If graphify-out/graph.json exists, run `graphify query` before source searches/reads."
        if "graphify" in cfg.extra_rules
        else "\n- Follow AGENTS.md."
    )
    graphify_update = (
        "\n- After code modifications, ensure `graphify update .` is executed."
        if ("graphify" in cfg.extra_rules and ag.enable_write)
        else ""
    )
    skills_line = (
        f"\n- Preferred skills for this role: {', '.join(f'`{s}`' for s in ag.skills)}."
        if ag.skills
        else ""
    )

    main_agent_val = "true" if ag.id in ("lead-architect", "orchestrator") else "false"
    return (
        f"---\n"
        f"name: {ag.id}\n"
        f"description: \"{ag.title}\"\n"
        f"model: {model_tier}\n"
        f"mainAgent: {main_agent_val}\n"
        f"subagent: true\n"
        f"tools:\n"
        f"{tools_yaml}\n"
        f"---\n\n"
        f"# Agent System Instructions\n\n"
        f"Project: **{cfg.project_name}** ({cfg.tech_stack})\n"
        f"- **Role**: {ag.role}\n"
        f"- **Preferred Model**: `{ag.agy_model}` (Tier: `{model_tier}`)"
        f"{fallback_line}\n"
        f"- **Mission**: {ag.mission}\n"
        f"- **Context & Scope**: {ag.context_scope}\n"
        f"- **Completion Criteria**: {ag.goal_criteria}"
        f"{skills_line}"
        f"{graphify_line}"
        f"{graphify_update}\n"
    )


def build_single_agent_toml(cfg: TeamConfig, ag: AgentSpec) -> str:
    """
    Sinh file `.agents/agents/<role>/agent.toml` theo đúng chuẩn Codex của Orpheus / Act2Morse:
    model, model_reasoning_effort, developer_instructions
    """
    graphify_note = (
        " If graphify-out/graph.json exists, run graphify query before source searches/reads "
        "and read only lines the graph or earlier reads located."
        if "graphify" in cfg.extra_rules
        else ""
    )
    if "graphify" in cfg.extra_rules and ag.enable_write:
        graphify_note += " After modifying code, run graphify update .; expected graph rewrites are not churn."

    fallback_note = (
        f"Fallback Chain: {format_fallback_chain(ag.fallback_chain)}\n"
        if ag.fallback_chain
        else ""
    )
    instructions = (
        f"Role: {ag.role} for {cfg.project_name}.\n"
        f"{fallback_note}"
        f"Mission: {ag.mission}\n"
        f"Scope: {ag.context_scope}\n"
        f"Completion Criteria: {ag.goal_criteria}\n"
        f"Project Context: {cfg.project_context}\n"
        f"Follow AGENTS.md.{graphify_note}"
    )

    return (
        f'model = "{ag.codex_model}"\n'
        f'model_reasoning_effort = "{ag.reasoning_effort}"\n'
        f'developer_instructions = """\n'
        f"{instructions}\n"
        f'"""\n'
    )


def build_codex_config_toml(cfg: TeamConfig) -> str:
    """
    Sinh file `.codex/config.toml` theo đúng chuẩn Orpheus / Act2Morse:
    - Main session model + developer_instructions ở đầu
    - [agents] enabled = true, max_concurrent_threads_per_session = 3
    - [agents.<role>] description = ..., config_file = "../.agents/agents/<role>/agent.toml"
    """
    lead = next((a for a in cfg.agents if a.id == "orchestrator"), cfg.agents[0])
    graphify_note = (
        "\nWhen graphify-out/graph.json exists, run graphify query before source searches/reads; "
        "read only lines located by the graph or earlier reads. Include this rule in every "
        "subagent prompt exploring code. Rebuild with graphify update . after code changes."
        if "graphify" in cfg.extra_rules
        else ""
    )

    lines = [
        f'model = "{lead.codex_model}"',
        f'model_reasoning_effort = "{lead.reasoning_effort}"',
        'developer_instructions = """',
        f"Act as {cfg.project_name}'s multi-agent team lead. Execute in 2 phases via host-native [agents] orchestration:",
        "Phase 1: Run a bounded 2-round debate between lead-architect (proposing RFC & plan) and lead-critic (stress-testing assumptions and YAGNI simplicity) to reach CONSENSUS_REACHED.",
        "Phase 2: Hand off the approved blueprint to orchestrator, who coordinates searcher (scout), designer (UI/UX), implementer (TDD), reviewer (code quality), and committer (conventional commits).",
        "Allow parallel fan-out for independent reads; enforce serialized single-writer edits on shared files, followed by independent verification and commit.",
        "Consider a workflow graph only when the host requires gate enforcement, state checkpointing/restoration, or systematic retry loops.",
        "Keep changes small, validate integration, and resolve review findings before claiming completion.",
        f"Project Context: {cfg.project_context}",
        f"Primary Goal: {cfg.project_goal}",
        f"Follow AGENTS.md.{graphify_note}",
        '"""',
        "",
        "[agents]",
        "enabled = true",
        "max_concurrent_threads_per_session = 3",
        "",
    ]

    for ag in cfg.agents:
        lines.extend(
            [
                f"[agents.{ag.id}]",
                f'description = "{ag.title}"',
                f'config_file = "../.agents/agents/{ag.id}/agent.toml"',
                "",
            ]
        )

    return "\n".join(lines)


def build_claude_agent_md(cfg: TeamConfig, ag: AgentSpec) -> str:
    """Sinh file .claude/agents/<id>.md theo chuẩn Claude Code."""
    base_tools = "Read, Edit, Write, Bash, Grep, Glob" if ag.enable_write else "Read, Grep, Glob, Bash"
    tools_str = base_tools + (", Agent" if ag.enable_subagents else "")
    model_line = f"model: {ag.claude_model}\n" if ag.claude_model != "inherit" else ""
    skills_str = ", ".join(ag.skills) if ag.skills else "Context-dependent"
    fallback_str = format_fallback_chain(ag.fallback_chain)
    return (
        f"---\n"
        f"name: {ag.id}\n"
        f"description: \"{ag.title} — {ag.role}\"\n"
        f"tools: {tools_str}\n"
        f"{model_line}"
        f"---\n\n"
        f"# {ag.id.replace('-', ' ').title()} ({cfg.project_name})\n\n"
        f"- **Mission**: {ag.mission}\n"
        f"- **Fallback Chain**: `{fallback_str}`\n"
        f"- **Context & Scope**: {ag.context_scope}\n"
        f"- **Goal & Completion Criteria**: {ag.goal_criteria}\n"
        f"- **Preferred Skills**: {skills_str}\n"
        f"- Adhere to the Execution Concurrency & Ordering Contract in `AGENTS.md` and `.agents/README.md`.\n"
        f"- Follow `AGENTS.md` and `.agents/README.md`.\n"
    )


def build_agy_skills_json(cfg: TeamConfig) -> Dict:
    """Sinh file .agents/skills.json chuẩn Antigravity."""
    parent_to_skills: Dict[str, List[str]] = {}
    home_str = str(Path.home())

    for s in cfg.selected_skills:
        p_dir = s["parent_dir"]
        if p_dir.startswith(home_str):
            p_dir = "~" + p_dir[len(home_str) :]
        parent_to_skills.setdefault(p_dir, [])
        if s["name"] not in parent_to_skills[p_dir]:
            parent_to_skills[p_dir].append(s["name"])

    entries = [{"path": ".agents/skills"}]
    for p_dir, s_names in sorted(parent_to_skills.items()):
        if p_dir == ".agents/skills":
            continue
        entries.append(
            {
                "path": p_dir,
                "include_only": sorted(s_names),
            }
        )
    return {"entries": entries}


def build_commit_restrictions_rule() -> str:
    return (
        "---\n"
        "description: Prohibits committing AGENTS.md, SKILL.md, docs, or ui.md to version control\n"
        "trigger: always_on\n"
        "---\n\n"
        "# Commit Restrictions\n\n"
        "1. **NEVER stage or commit**:\n"
        "   - `AGENTS.md`\n"
        "   - `SKILL.md` (or any file named `SKILL.md` across the entire workspace)\n"
        "   - `docs` or `docs/`\n"
        "   - `ui.md`\n"
        "2. **Local Preservation**:\n"
        "   - These files must remain in the local workspace filesystem for local use.\n"
    )


def apply_skills_to_workspace(cfg: TeamConfig, project_path: Path, dry_run: bool = False) -> List[str]:
    """
    Nếu người dùng chọn `symlink` hoặc `copy`, gắn trực tiếp các skills đã chọn vào
    `.agents/skills/<skill_name>` (và `.claude/skills/<skill_name>` nếu bật claude)
    để project có thể truy cập tức thì giống như Hephaestus!
    """
    applied_paths: List[str] = []
    if cfg.skill_apply_mode == "json-only":
        return applied_paths

    agents_skills_dir = project_path / ".agents" / "skills"
    if not dry_run:
        agents_skills_dir.mkdir(parents=True, exist_ok=True)

    for s in cfg.selected_skills:
        src_dir = Path(s["skill_dir"])
        if not src_dir.exists():
            continue
        dest_dir = agents_skills_dir / s["name"]
        if src_dir.resolve() == dest_dir.resolve():
            continue

        applied_paths.append(str(dest_dir))
        if dry_run:
            continue

        if dest_dir.is_symlink() or dest_dir.is_file():
            dest_dir.unlink()

        if cfg.skill_apply_mode == "symlink":
            if not dest_dir.exists():
                dest_dir.symlink_to(src_dir)
        elif cfg.skill_apply_mode == "copy":
            shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)

    return applied_paths


def build_subagent_payload(cfg: TeamConfig, ag: AgentSpec) -> Dict:
    """Sinh payload JSON cho define_subagent / invoke_subagent của Antigravity."""
    model_tier = _to_agy_model_tier(ag.agy_model)
    system_prompt = (
        f"Bạn là **{ag.role}** (`{ag.id}`) trong dự án **{cfg.project_name}**.\n\n"
        f"## 1. Ngữ cảnh Dự án (Project Context)\n"
        f"- **Tech Stack**: {cfg.tech_stack}\n"
        f"- **Bối cảnh chung**: {cfg.project_context}\n"
        f"- **Mục tiêu dự án**: {cfg.project_goal}\n\n"
        f"## 2. Nhiệm vụ & Phạm vi của bạn (Mission & Scope)\n"
        f"- **Nhiệm vụ cốt lõi**: {ag.mission}\n"
        f"- **Phạm vi hoạt động (Scope)**: {ag.context_scope}\n"
        f"- **Skills ưu tiên sử dụng**: {', '.join(ag.skills) if ag.skills else 'None'}\n\n"
        f"## 3. Tiêu chí Hoàn thành (Completion Criteria)\n"
        f"{ag.goal_criteria}\n\n"
        f"## 4. Nguyên tắc Phối hợp Đội ngũ\n"
        f"- Bám sát quy ước chung trong `AGENTS.md` và `.agents/README.md`.\n"
        f"- Quyền sửa đổi file: {'Có quyền ghi file (Write enabled).' if ag.enable_write else 'Chế độ CHỈ ĐỌC (Read-Only). Tuyệt đối không tự ý sửa đổi file mã nguồn.'}\n"
        f"- Báo cáo kết quả ngắn gọn, có cấu trúc, kèm đường dẫn file và dòng code cụ thể.\n"
    )
    return {
        "define_subagent": {
            "Name": ag.id,
            "Description": f"{ag.role}: {ag.mission}",
            "SystemPrompt": system_prompt,
            "EnableWriteTools": ag.enable_write,
            "EnableSubagentTools": ag.enable_subagents,
            "EnableMCPTools": ag.enable_mcp,
        },
        "invoke_subagent_defaults": {
            "TypeName": ag.id,
            "Role": ag.role,
            "Model": model_tier,
            "Workspace": ag.workspace_mode,
        },
        "metadata": {
            "provider": ag.provider,
            "requested_model": ag.agy_model,
            "fallback_chain": ag.fallback_chain,
            "skills": ag.skills,
        },
    }


def build_subagent_doc_md(cfg: TeamConfig, ag: AgentSpec) -> str:
    """Sinh file .agents/subagents/<id>.md."""
    model_tier = _to_agy_model_tier(ag.agy_model)
    skills_str = ", ".join(ag.skills) if ag.skills else "None"
    fallback_str = format_fallback_chain(ag.fallback_chain)
    return (
        f"# Antigravity Subagent Spec: `{ag.id}` ({ag.role})\n\n"
        f"- **Role**: {ag.role}\n"
        f"- **Provider / Model**: `{ag.provider}` / `{ag.agy_model}` (Antigravity `Model`: `{model_tier}`)\n"
        f"- **Workspace Mode**: `{ag.workspace_mode}`\n"
        f"- **EnableWriteTools**: `{ag.enable_write}` | **EnableSubagentTools**: `{ag.enable_subagents}` | **EnableMCPTools**: `{ag.enable_mcp}`\n"
        f"- **Fallback Chain**: `{fallback_str}`\n\n"
        f"## System Prompt\n\n"
        f"Bạn là **{ag.role}** (`{ag.id}`) trong dự án **{cfg.project_name}**.\n\n"
        f"### 1. Ngữ cảnh Dự án (Project Context)\n"
        f"- **Tech Stack**: {cfg.tech_stack}\n"
        f"- **Bối cảnh**: {cfg.project_context}\n"
        f"- **Mục tiêu**: {cfg.project_goal}\n\n"
        f"### 2. Nhiệm vụ & Phạm vi (Mission & Scope)\n"
        f"- **Nhiệm vụ cốt lõi**: {ag.mission}\n"
        f"- **Phạm vi hoạt động**: {ag.context_scope}\n"
        f"- **Skills ưu tiên**: {skills_str}\n\n"
        f"### 3. Tiêu chí Hoàn thành (Completion Criteria)\n"
        f"{ag.goal_criteria}\n\n"
        f"### 4. Nguyên tắc Phối hợp Đội ngũ\n"
        f"- Bám sát quy ước chung trong `AGENTS.md`.\n"
        f"- Quyền sửa đổi file: {'Có quyền ghi file (Write enabled).' if ag.enable_write else 'Chế độ CHỈ ĐỌC (Read-Only). Tuyệt đối không tự ý sửa đổi file mã nguồn.'}\n"
        f"- Báo cáo kết quả ngắn gọn, có cấu trúc, kèm đường dẫn file và dòng code cụ thể.\n"
    )


def build_team_orchestrator_skill(cfg: TeamConfig) -> str:
    """Sinh file .agents/skills/team-orchestrator/SKILL.md chuẩn 2 Pha."""
    en_desc = (
        "Activate and coordinate the 2-Phase AI Team (Phase 1: Bounded 2-round debate between lead-architect "
        "and lead-critic; Phase 2: orchestrator coordinates searcher, designer, implementer, reviewer, and committer). "
        "Use this skill when asked to run the team, debate solutions, or orchestrate multi-agent development."
    )
    vi_desc = (
        "Kích hoạt và điều phối Đội ngũ AI 2 Pha (Phase 1: Cặp Lead phản biện 2 vòng giữa lead-architect & lead-critic; "
        "Phase 2: orchestrator điều phối searcher, designer, implementer, reviewer, committer). "
        "Sử dụng skill này khi người dùng yêu cầu chạy đội agent, phản biện giải pháp, hoặc điều phối multi-agent."
    )
    desc = tr(en_desc, vi_desc)

    en_content = f"""---
name: team-orchestrator
description: >-
  {desc}
---

# Team Orchestrator Skill — {cfg.project_name}

This skill defines the canonical 2-phase orchestration protocol: **Bounded 2-Round Strategic Debate (Phase 1)** before handing off to **Hierarchical Execution (Phase 2)** via host-native multi-agent coordination.

## 1. Team Roster

### Phase 1: Strategic Debate Pair
- **`lead-architect`** (Lead Solution Architect & Planner):
  - Model: `gemini-4-argon-high` / `gpt-6-astra` (Tier: `pro` / `high`)
  - Permissions: Read-Only (`EnableWriteTools=False`, `EnableSubagentTools=False`, `EnableMCPTools=True`)
  - Mission: Formulate initial architecture proposals, technical design blueprints, module contracts, and task breakdowns.
- **`lead-critic`** (Lead Technical Critic & Challenger):
  - Model: `gemini-3.1-pro-high` / `gpt-6.1-sol` (Tier: `pro` / `xhigh`)
  - Permissions: Read-Only (`EnableWriteTools=False`, `EnableSubagentTools=False`, `EnableMCPTools=False`)
  - Mission: Stress-test assumptions, identify blind spots, security vulnerabilities, edge cases, and YAGNI simplicity.

### Phase 2: Hierarchical Execution
- **`orchestrator`** (Lead Execution Orchestrator):
  - Model: `gemini-4-argon-high` / `gpt-6-astra` (Tier: `pro` / `high`)
  - Permissions: Coordination (`EnableWriteTools=False`, `EnableSubagentTools=True`, `EnableMCPTools=True`)
  - Mission: Coordinate worker subagents via host-native orchestration; enforce execution ordering without direct code edits.
- **`searcher`** (Primary Documentation & Codebase Scout):
  - Model: `gemini-3.8-flash-medium` / `gpt-6-luna` (Tier: `flash` / `medium`, Read-Only)
- **`designer`** (UI/UX & Anti-Slop Visual Designer):
  - Model: `gemini-3.8-flash-high` / `gpt-6-sol` (Tier: `flash` / `xhigh`, Read + Write, Workspace: `share`)
- **`implementer`** (Senior Feature & TDD Implementer):
  - Model: `gemini-3.8-flash-high` / `gpt-6-sol` (Tier: `flash` / `xhigh`, Read + Write, Workspace: `share`)
- **`reviewer`** (Independent Code Quality & Security Reviewer):
  - Model: `gemini-3.1-pro-high` / `gpt-6.1-sol` (Tier: `pro` / `xhigh`, Read-Only)
- **`committer`** (Conventional Git Committer):
  - Model: `gemini-3.7-flash` / `gpt-6-luna` (Tier: `flash_lite` / `low`, Read-Only)

---

## 2. Canonical 2-Phase Execution Workflow

```
[User Request]
       │
       ▼
═══════════════════════════════════════════════════════════════
PHASE 1: BOUNDED 2-ROUND LEAD DEBATE (STRATEGIC DEBATE)
═══════════════════════════════════════════════════════════════
  [Round 1]
    1. `lead-architect`: Formulate initial RFC & Task Breakdown
    2. `lead-critic`   : Stress-test assumptions & edge cases
  [Round 2]
    3. `lead-architect`: Address critiques & produce Final Blueprint
    4. `lead-critic`   : Final validation & grant `CONSENSUS_REACHED: APPROVED`
       │
       ▼
═══════════════════════════════════════════════════════════════
PHASE 2: HIERARCHICAL EXECUTION (ORCHESTRATOR + SUBAGENTS)
═══════════════════════════════════════════════════════════════
    5. `orchestrator` receives approved blueprint
    6. `searcher` scouts codebase / docs (parallel fan-out)
    7. `designer` designs UI/UX & visual styling (sequential / single-writer)
    8. `implementer` writes Unit Tests (Red) -> Code (Green) -> Refactor (sequential / single-writer)
    9. `reviewer` independently validates Spec & Standards
   10. `committer` packages atomic Conventional Commits
```

---

## 3. Host-Native Orchestration Mechanisms

`agent-team` acts as a multi-harness scaffold and generator without a custom runtime engine:
- **`agy` (Antigravity CLI)**: Uses `invoke_subagent` and `send_message` with subagent definitions in `.agents/agents/`.
- **`codex` (OpenAI Codex)**: Uses `[agents]` section in `.codex/config.toml` to launch multi-agent threads natively.
- **`claude` (Claude Code)**: Reads subagent instructions from `.claude/agents/*.md` linked via `CLAUDE.md`.

---

## 4. Execution Concurrency & Ordering Contract

1. **Parallel Read Fan-Out**: Independent codebase scouting and documentation search tasks (`searcher`) can fan out in parallel.
2. **Ordered Shared-File Edits (Single-Writer)**: Implementation tasks (`implementer`, `designer`) that modify shared files or contracts must execute sequentially with strict single-writer boundaries.
3. **Ordered Verification & Commit**: `reviewer` independently validates diffs against Spec and Coding Standards; once `APPROVED`, `committer` packages atomic Conventional Commits.

---

## 5. Workflow Graph Decision Boundary

A graph-based state machine is NOT required for standard linear development. Consider an external workflow graph only when the target environment requires:
- **Gate Enforcement**: Programmatic host quality gates enforcing formal criteria before phase transitions.
- **State Checkpointing & Resumption**: Checkpointing execution state to disk to survive host restarts or long pauses.
- **Systematic Retry Loops**: Automated remediation cycles that re-dispatch worker agents upon verification failure.
"""

    vi_content = f"""---
name: team-orchestrator
description: >-
  {desc}
---

# Team Orchestrator Skill — {cfg.project_name}

Skill này hướng dẫn quy trình điều phối chuẩn 2 Pha: **Phản biện Chiến lược 2 Vòng (Phase 1)** trước khi chuyển giao cho **Hạ tầng Thực thi Phân cấp (Phase 2)** thông qua điều phối native của host.

## 1. Cấu hình Đội ngũ (Team Roster)

### Pha 1: Cặp Lead Phản biện Kiến trúc (Strategic Debate Pair)
- **`lead-architect`** (Kiến trúc sư trưởng & Hoạch định giải pháp):
  - Model: `gemini-4-argon-high` / `gpt-6-astra` (Tier: `pro` / `high`)
  - Quyền hạn: Read-Only (`EnableWriteTools=False`, `EnableSubagentTools=False`, `EnableMCPTools=True`)
  - Nhiệm vụ: Đề xuất kiến trúc, module contracts, RFC và kế hoạch phân rã task.
- **`lead-critic`** (Phản biện trưởng & Thẩm định rủi ro):
  - Model: `gemini-3.1-pro-high` / `gpt-6.1-sol` (Tier: `pro` / `xhigh`)
  - Quyền hạn: Read-Only (`EnableWriteTools=False`, `EnableSubagentTools=False`, `EnableMCPTools=False`)
  - Nhiệm vụ: Stress-test giải pháp, vạch trần điểm mù, lỗ hổng bảo mật, nguy cơ over-engineering (YAGNI).

### Pha 2: Điều phối Thực thi Phân cấp (Hierarchical Execution)
- **`orchestrator`** (Tổng điều phối viên thực thi):
  - Model: `gemini-4-argon-high` / `gpt-6-astra` (Tier: `pro` / `high`)
  - Quyền hạn: Điều phối (`EnableWriteTools=False`, `EnableSubagentTools=True`, `EnableMCPTools=True`)
- **`searcher`** (Trinh sát mã nguồn & Tra cứu tài liệu):
  - Model: `gemini-3.8-flash-medium` / `gpt-6-luna` (Tier: `flash` / `medium`, Read-Only)
- **`designer`** (Kỹ sư thiết kế UI/UX & Bản sắc thị giác Anti-Slop):
  - Model: `gemini-3.8-flash-high` / `gpt-6-sol` (Tier: `flash` / `xhigh`, Read + Write, Workspace: `share`)
- **`implementer`** (Kỹ sư thực thi tính năng & TDD):
  - Model: `gemini-3.8-flash-high` / `gpt-6-sol` (Tier: `flash` / `xhigh`, Read + Write, Workspace: `share`)
- **`reviewer`** (Kiểm định viên chất lượng & Bảo mật độc lập):
  - Model: `gemini-3.1-pro-high` / `gpt-6.1-sol` (Tier: `pro` / `xhigh`, Read-Only)
- **`committer`** (Chuyên viên đóng gói Git Commit):
  - Model: `gemini-3.7-flash` / `gpt-6-luna` (Tier: `flash_lite` / `low`, Read-Only)

---

## 2. Quy trình Thực thi Chuẩn 2 Pha

```
[User Request]
       │
       ▼
═══════════════════════════════════════════════════════════════
PHA 1: CẶP LEAD PHẢN BIỆN 2 VÒNG (STRATEGIC 2-ROUND DEBATE)
═══════════════════════════════════════════════════════════════
  [Vòng 1]
    1. `lead-architect`: Xuất bản RFC Đề xuất Kiến trúc & Phân rã Task
    2. `lead-critic`   : Stress-test, vạch ra các điểm mù & rủi ro kỹ thuật
  [Vòng 2]
    3. `lead-architect`: Tiếp thu phản biện, hoàn thiện Final Blueprint
    4. `lead-critic`   : Thẩm định lần cuối & Cấp `CONSENSUS_REACHED: APPROVED`
       │
       ▼
═══════════════════════════════════════════════════════════════
PHA 2: ĐIỀU PHỐI THỰC THI PHÂN CẤP (ORCHESTRATOR + SUBAGENTS)
═══════════════════════════════════════════════════════════════
    5. `orchestrator` tiếp nhận Final Blueprint đã được duyệt
    6. `searcher` trinh sát chính xác file:dòng trong codebase (fan-out song song)
    7. `designer` thiết kế UI/UX & bản sắc thị giác Anti-Slop (tuần tự / single-writer)
    8. `implementer` viết Unit Test (Red) -> Code tối giản (Green) -> Refactor (tuần tự / single-writer)
    9. `reviewer` kiểm định độc lập (Spec Compliance & Coding Standards)
   10. `committer` đóng gói Conventional Commits và nghiệm thu
```

---

## 3. Cơ Chế Điều Phối Host-Native

`agent-team` vận hành thuần túy là bộ scaffold và generator đa harness không runtime tùy biến:
- **`agy` (Antigravity CLI)**: Sử dụng các công cụ native `invoke_subagent` và `send_message` với định nghĩa tại `.agents/agents/`.
- **`codex` (OpenAI Codex)**: Kích hoạt luồng đa agent native thông qua block `[agents]` trong `.codex/config.toml`.
- **`claude` (Claude Code)**: Đọc hồ sơ subagent tại `.claude/agents/*.md` thông qua `CLAUDE.md`.

---

## 4. Giao Thức Đồng Thời & Thứ Tự Thực Thi (Concurrency & Ordering Contract)

1. **Parallel Read Fan-Out**: Các tác vụ trinh sát mã nguồn và tra cứu tài liệu độc lập (`searcher`) có thể chạy song song (fan-out).
2. **Ordered Shared-File Edits (Single-Writer)**: Tác vụ triển khai (`implementer`, `designer`) khi sửa đổi file chung hoặc module contracts phải thực thi tuần tự theo nguyên tắc đơn ghi (single-writer).
3. **Ordered Verification & Commit**: `reviewer` kiểm định độc lập 2 trục; khi `APPROVED`, `committer` đóng gói atomic Conventional Commit.

---

## 5. Ranh Giới Quyết Định Workflow Graph (Workflow Graph Decision Boundary)

Mô hình máy trạng thái dạng đồ thị (workflow graph) không bắt buộc cho quy trình phát triển thông thường. Chỉ cân nhắc tích hợp workflow graph khi môi trường thực thi yêu cầu:
- **Cổng Chặn (Gate Enforcement)**: Thực thi các cổng kiểm soát chất lượng có tính cưỡng chế của host, ngăn chặn chuyển pha khi chưa đủ điều kiện.
- **Lưu/Khôi Phục State (State Checkpointing & Resumption)**: Lưu checkpoint trạng thái thực thi bền vững xuống đĩa để có thể tạm dừng, phục hồi sau khi khởi động lại host.
- **Vòng Lặp Thử Lại Có Hệ Thống (Systematic Retry Loops)**: Quản lý chu trình tự động sửa lỗi và điều phối lại có hệ thống khi bước kiểm định hoặc review chưa đạt.
"""
    return vi_content if CURRENT_LANG == "vi" else en_content


def write_project_configuration(cfg: TeamConfig, dry_run: bool = False) -> List[str]:
    project_path = Path(cfg.project_path).resolve()
    created_files: List[str] = []

    def save(rel_path: str, content: str) -> None:
        full_path = project_path / rel_path
        created_files.append(str(full_path))
        if dry_run:
            return
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")

    # Đọc AGENTS.md cũ (nếu có) để bảo toàn các mục hướng dẫn riêng của repo
    existing_agents_md: Optional[str] = None
    agents_md_path = project_path / "AGENTS.md"
    if agents_md_path.exists():
        try:
            existing_agents_md = agents_md_path.read_text(encoding="utf-8")
        except Exception:
            existing_agents_md = None

    # Compute root AGENTS.md content BEFORE calling save on any file so if
    # build_root_agents_md raises ValueError, zero files on disk are created or modified!
    agents_md_content = build_root_agents_md(cfg, existing_agents_md)

    # 1. Root AGENTS.md
    save("AGENTS.md", agents_md_content)

    # 2. Chuẩn .agents/ (Dùng chung cho cả Antigravity `agy` và OpenAI `codex`)
    save(".agents/README.md", build_agents_readme_md(cfg))
    save(".agents/agents.json", json.dumps(build_agents_json(cfg), indent=2, ensure_ascii=False) + "\n")
    save(".agents/skills.json", json.dumps(build_agy_skills_json(cfg), indent=2, ensure_ascii=False) + "\n")

    for ag in cfg.agents:
        save(f".agents/agents/{ag.id}/agent.md", build_single_agent_md(cfg, ag))
        save(f".agents/agents/{ag.id}/agent.toml", build_single_agent_toml(cfg, ag))
        save(f".agents/subagents/{ag.id}.json", json.dumps(build_subagent_payload(cfg, ag), indent=2, ensure_ascii=False) + "\n")
        save(f".agents/subagents/{ag.id}.md", build_subagent_doc_md(cfg, ag))

    # Tự động đồng bộ / sinh team-orchestrator skill chuẩn 2 Pha cho project
    save(".agents/skills/team-orchestrator/SKILL.md", build_team_orchestrator_skill(cfg))

    if cfg.add_commit_restrictions:
        commit_rule_path = project_path / ".agents" / "rules" / "commit-restrictions.md"
        if commit_rule_path.exists():
            created_files.append(str(commit_rule_path))
        else:
            save(".agents/rules/commit-restrictions.md", build_commit_restrictions_rule())

    # 3. Chuẩn OpenAI Codex CLI (.codex/config.toml)
    if "codex" in cfg.harnesses:
        save(".codex/config.toml", build_codex_config_toml(cfg))

    # 4. Chuẩn Anthropic Claude Code (CLAUDE.md & .claude/agents/*.md)
    if "claude" in cfg.harnesses:
        claude_md = (
            f"# CLAUDE.md — {cfg.project_name}\n\n"
            f"See @AGENTS.md and @.agents/README.md for project guidelines, architecture, and agent roles.\n"
        )
        save("CLAUDE.md", claude_md)
        for ag in cfg.agents:
            save(f".claude/agents/{ag.id}.md", build_claude_agent_md(cfg, ag))

    # 5. Apply Skills vào `.agents/skills/`
    skill_paths = apply_skills_to_workspace(cfg, project_path, dry_run=dry_run)
    if skill_paths:
        created_files.append(str(project_path / ".agents/skills/"))

    # 6. Lưu .agents/team-config.json để dễ dàng chỉnh sửa về sau
    save(".agents/team-config.json", json.dumps(asdict(cfg), indent=2, ensure_ascii=False) + "\n")

    return created_files


# ---------------------------------------------------------------------------
# Non-Interactive Preset & CLI Subcommands
# ---------------------------------------------------------------------------
def build_preset_config(
    target_dir: Path,
    goal: str,
    context: str,
    harnesses: List[str],
    bundles: List[str],
    skill_apply_mode: str = "symlink",
) -> TeamConfig:
    project_path = target_dir.resolve()
    project_name = project_path.name
    tech_stack = detect_tech_stack(project_path)
    discovered = discover_local_skills()

    active_templates = get_agent_templates()
    agents: List[AgentSpec] = []
    preset_roles = (
        "lead-architect",
        "lead-critic",
        "orchestrator",
        "reviewer",
        "designer",
        "implementer",
        "searcher",
        "committer",
    )
    for role_id in preset_roles:
        tpl = active_templates[role_id]
        agents.append(
            AgentSpec(
                id=role_id,
                title=tpl["title"],
                role=tpl["role"],
                mission=tpl["mission"],
                provider=tpl["provider"],
                agy_model=tpl["agy_model"],
                claude_model=tpl["claude_model"],
                codex_model=tpl["codex_model"],
                reasoning_effort=tpl["reasoning_effort"],
                context_scope=tpl["context_scope"],
                goal_criteria=tpl["goal_criteria"],
                enable_write=bool(tpl["enable_write"]),
                enable_subagents=bool(tpl["enable_subagents"]),
                enable_mcp=bool(tpl["enable_mcp"]),
                workspace_mode=str(tpl["workspace_mode"]),
                agy_tools=list(tpl["agy_tools"]),
                skills=list(tpl["skills"]),
                fallback_chain=list(tpl.get("fallback_chain", [])),
            )
        )

    skill_names_set = set()
    for b_key in bundles:
        if b_key in SKILL_BUNDLES:
            for s_name in SKILL_BUNDLES[b_key]["skills"]:  # type: ignore[index]
                skill_names_set.add(s_name)
    for ag in agents:
        for s_name in ag.skills:
            skill_names_set.add(s_name)

    resolved_skills: List[Dict[str, str]] = [
        discovered[s_name] for s_name in sorted(skill_names_set) if s_name in discovered
    ]

    existing_cfg_path = project_path / ".agents" / "team-config.json"
    existing_data: Optional[Dict] = None
    if existing_cfg_path.exists():
        try:
            existing_data = json.loads(existing_cfg_path.read_text(encoding="utf-8"))
        except Exception:
            existing_data = None

    extra_rules = existing_data.get("extra_rules", ["graphify", "drawio-erd"]) if existing_data else ["graphify", "drawio-erd"]
    add_commit_restrictions = existing_data.get("add_commit_restrictions", False) if existing_data else False
    if existing_data:
        if not context and existing_data.get("project_context"):
            context = existing_data["project_context"]
        if not goal and existing_data.get("project_goal"):
            goal = existing_data["project_goal"]

    return TeamConfig(
        project_name=project_name,
        project_path=str(project_path),
        tech_stack=tech_stack,
        project_context=context
        or tr(
            f"{project_name} ({tech_stack}). Keep changes small and complete, prioritize TDD and independent code review.",
            f"Dự án {project_name} ({tech_stack}). Giữ thay đổi nhỏ gọn, ưu tiên TDD và kiểm định độc lập.",
        ),
        project_goal=goal
        or tr(
            f"Develop, test, and maintain {project_name} with 2-phase lead debate (lead-architect & lead-critic) and execution team (orchestrator, searcher, implementer, reviewer, committer).",
            f"Phát triển, kiểm thử và duy trì {project_name} qua mô hình 2 pha: phản biện lead (lead-architect & lead-critic) và đội thực thi (orchestrator, searcher, implementer, reviewer, committer).",
        ),
        extra_rules=extra_rules,
        harnesses=harnesses,
        skill_apply_mode=skill_apply_mode,
        add_commit_restrictions=add_commit_restrictions,
        selected_skill_bundles=bundles,
        selected_skills=resolved_skills,
        agents=agents,
        updated_at=datetime.now().isoformat(timespec="seconds"),
    )


def cmd_list_skills() -> None:
    banner()
    discovered = discover_local_skills()
    by_plugin: Dict[str, List[Dict[str, str]]] = {}
    for s in discovered.values():
        by_plugin.setdefault(s["plugin"], []).append(s)

    print(
        tr(
            f"\nFound {c(str(len(discovered)), BOLD + GREEN)} local skills on this machine:\n",
            f"\nTìm thấy tổng cộng {c(str(len(discovered)), BOLD + GREEN)} skills trên máy:\n",
        )
    )
    for plugin, items in sorted(by_plugin.items()):
        print(c(tr(f"📦 Source/Plugin: {plugin}", f"📦 Nguồn/Plugin: {plugin}"), BOLD + CYAN))
        for item in sorted(items, key=lambda x: x["name"]):
            print(f"   • {BOLD}{item['name']}{RESET}: {item['description']}")
        print()


def cmd_status(target_dir: Path) -> None:
    # No banner per user request: "khi gõ agt status không hiện banner"
    project_path = target_dir.resolve()
    cfg_file = project_path / ".agents" / "team-config.json"
    agents_json = project_path / ".agents" / "agents.json"

    # 1. 7 columns (art, animal name, roles, model, reasoning effects), 4 rows (agy, codex, claude, fallback)
    agents_data = None
    if cfg_file.exists():
        try:
            data = json.loads(cfg_file.read_text(encoding="utf-8"))
            agents_data = data.get("agents", [])
        except Exception:
            pass
    print(render_7col_agent_grid(agents_data=agents_data, project_path=project_path))

    # 2. Status ở dưới
    if cfg_file.exists():
        data = json.loads(cfg_file.read_text(encoding="utf-8"))
        proj_name = data.get("project_name", project_path.name)
        stored_goal = str(data.get("project_goal", ""))
        display_goal = (
            stored_goal
            if _matches_current_lang(stored_goal)
            else tr(
                f"Develop, test, and maintain {proj_name} through a directly orchestrated Multi-Agent team.",
                f"Phát triển, kiểm thử và duy trì {proj_name} thông qua đội ngũ Multi-Agent điều phối trực tiếp.",
            )
        )
        print(
            c(
                tr(
                    f"📊 AI Team Status — {proj_name} ({data.get('project_path', project_path)}):",
                    f"📊 Trạng thái Đội ngũ AI — {proj_name} ({data.get('project_path', project_path)}):",
                ),
                BOLD + GREEN,
            )
        )
        print(f"  • Tech Stack : {c(data.get('tech_stack', 'Unknown'), BOLD)}")
        print(f"  • {tr('Goal       ', 'Mục tiêu   ')}: {display_goal}")
        print(f"  • {tr('Harnesses  ', 'Công cụ    ')}: {', '.join(data.get('harnesses', []))}")
        print(f"  • Skill Mode : {data.get('skill_apply_mode')}")
        print(f"  • {tr('Updated    ', 'Cập nhật   ')}: {data.get('updated_at')}")

        skills = [s["name"] for s in data.get("selected_skills", [])]
        print(c(tr(f"\n🧩 Applied Skills ({len(skills)} active):", f"\n🧩 Skills đã gắn ({len(skills)} skills):"), BOLD + CYAN))
        print("  " + ", ".join(skills))
        print()
        return

    # If no team-config.json, show status info for unconfigured folder
    print(
        c(
            tr(
                f"ℹ️  Target: {project_path.name} ({project_path}) — [Standard 2-Phase 8-Role Catalog]",
                f"ℹ️  Thư mục: {project_path.name} ({project_path}) — [Bảng Roster 8 Roles Chuẩn 2 Pha]",
            ),
            BOLD + YELLOW,
        )
    )
    print(
        c(
            tr(
                "💡 Tip: Run `agt` or `agt init` to customize and deploy this team to the project.\n",
                "💡 Gợi ý: Gõ `agt` hoặc `agt init` để tùy biến và triển khai đội ngũ này vào dự án.\n",
            ),
            DIM + CYAN,
        )
    )


def parse_yaml_frontmatter(md_path: Path) -> Dict[str, str]:
    """Parse key-value pairs from a Markdown file's YAML frontmatter."""
    result: Dict[str, str] = {}
    try:
        text = md_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return result
    if not text.startswith("---"):
        return result
    parts = text.split("---", 2)
    if len(parts) < 3:
        return result
    for raw_line in parts[1].splitlines():
        line = raw_line.strip()
        if not line or line.startswith("-") or ":" not in line:
            continue
        k, v = line.split(":", 1)
        result[k.strip()] = v.strip().strip('"').strip("'")
    return result


def get_live_os_procs(project_path: Path) -> List[Dict[str, Any]]:
    """Scan /proc to find active agy, codex, claude, or python agent CLI processes."""
    proc_root = Path("/proc")
    running_procs: List[Dict[str, Any]] = []
    now_ts = datetime.now().timestamp()
    resolved_proj = project_path.resolve()

    if not proc_root.is_dir():
        return running_procs

    my_pid = str(os.getpid())

    for entry in proc_root.iterdir():
        if not entry.name.isdigit() or entry.name == my_pid:
            continue
        try:
            comm = (entry / "comm").read_text(encoding="utf-8", errors="ignore").strip()
            cmdline_bytes = (entry / "cmdline").read_bytes()
            cmdline_str = cmdline_bytes.replace(b"\x00", b" ").decode("utf-8", errors="ignore").strip()

            is_matched = comm in ("agy", "codex", "claude", "gemini")
            if not is_matched and ("agent_team.py" in cmdline_str or "agent_team" in comm):
                is_matched = True

            if not is_matched:
                continue

            status_text = (entry / "status").read_text(encoding="utf-8", errors="ignore")
            vmrss = "-"
            threads = "-"
            state = "-"
            for line in status_text.splitlines():
                if line.startswith("VmRSS:"):
                    kb = int(line.split()[1])
                    vmrss = f"{kb / 1024:.1f} MB" if kb >= 1024 else f"{kb} KB"
                elif line.startswith("Threads:"):
                    threads = line.split()[1]
                elif line.startswith("State:"):
                    state = line.split(":", 1)[1].strip()

            cwd_link = os.readlink(str(entry / "cwd"))
            stat_mtime = (entry / "stat").stat().st_mtime
            elapsed_sec = max(0, int(now_ts - stat_mtime))
            mins, secs = divmod(elapsed_sec, 60)
            hrs, mins = divmod(mins, 60)
            elapsed_str = f"{hrs:02d}:{mins:02d}:{secs:02d}" if hrs else f"{mins:02d}:{secs:02d}"

            in_proj = False
            try:
                in_proj = Path(cwd_link).resolve() == resolved_proj
            except Exception:
                pass

            running_procs.append(
                {
                    "pid": entry.name,
                    "comm": comm,
                    "cwd": cwd_link,
                    "cmdline": cmdline_str or comm,
                    "elapsed": elapsed_str,
                    "vmrss": vmrss,
                    "threads": threads,
                    "state": state,
                    "in_project": in_proj,
                }
            )
        except Exception:
            continue

    # Sort so processes belonging to THIS PROJECT appear first, then by PID integer
    running_procs.sort(key=lambda p: (not p["in_project"], int(p["pid"])))
    return running_procs


def detect_live_agent_occupancy(
    project_path: Path,
    manual_active: str = "",
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Detect currently active tasks and which role is occupying which task.
    Inspects ~/.gemini/antigravity-cli/brain/ for recent sessions, tool calls, and subagent invocations.
    Allows manual override/simulation via manual_active.
    """
    active_roles: Dict[str, Any] = {}
    recent_sessions: List[Dict[str, Any]] = []
    now_ts = datetime.now().timestamp()

    # 1. Apply manual active roles if supplied
    if manual_active:
        parts = [p.strip().lower() for p in manual_active.replace(";", ",").split(",") if p.strip()]
        for p in parts:
            canonical = ROLE_ALIASES.get(p, p)
            active_roles[canonical] = {
                "canonical": canonical,
                "role_raw": "",
                "prompt": tr(
                    "Active task (specified via --active)",
                    "Tác vụ đang chiếm giữ (chỉ định qua --active)",
                ),
                "is_manual": True,
            }

    # 2. Inspect Antigravity brain sessions
    brain_root = Path.home() / ".gemini" / "antigravity-cli" / "brain"
    if brain_root.is_dir():
        candidates: List[Tuple[float, Path]] = []
        for conv_dir in brain_root.iterdir():
            if not conv_dir.is_dir():
                continue
            tr_path = conv_dir / ".system_generated" / "logs" / "transcript.jsonl"
            if tr_path.exists():
                try:
                    candidates.append((tr_path.stat().st_mtime, conv_dir))
                except Exception:
                    pass
        candidates.sort(key=lambda x: x[0], reverse=True)

        for mtime, conv_dir in candidates[:5]:
            age_sec = max(0, int(now_ts - mtime))
            tr_path = conv_dir / ".system_generated" / "logs" / "transcript.jsonl"
            last_tool = "-"
            subagents_invoked: List[Dict[str, str]] = []
            lines: List[str] = []
            try:
                lines = tr_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                for ln in lines[-60:]:
                    try:
                        obj = json.loads(ln)
                    except Exception:
                        continue
                    for tc in obj.get("tool_calls", []) or []:
                        tname = tc.get("name", "")
                        if tname:
                            last_tool = tname
                        args_obj = tc.get("arguments") or tc.get("args") or {}
                        if isinstance(args_obj, str):
                            try:
                                args_obj = json.loads(args_obj)
                            except Exception:
                                args_obj = {}
                        if not isinstance(args_obj, dict):
                            args_obj = {}

                        if tname == "invoke_subagent":
                            tn = str(args_obj.get("TypeName", "subagent")).lower()
                            r = str(args_obj.get("Role", "")).strip().strip('"').strip("'")
                            p = str(args_obj.get("Prompt", "")).strip().replace("\n", " ")
                            p_clean = p.strip('"').strip("'").strip()
                            subagents_invoked.append({"type": tn, "role": r, "prompt": p_clean[:70]})
                            for kr in ROLE_ALIASES:
                                if kr in tn or kr in r.lower():
                                    canonical = ROLE_ALIASES[kr]
                                    active_roles[canonical] = {
                                        "canonical": canonical,
                                        "role_raw": r,
                                        "prompt": p_clean,
                                    }
                        elif age_sec < 180 and not manual_active:
                            # Heuristic based on active recent session tools (< 3 minutes)
                            if tname in ("write_file", "edit_file"):
                                target_path = str(args_obj.get("Path", "")).lower()
                                if any(ext in target_path for ext in (".css", ".scss", ".tailwind", "design", "style", "banner", "ui")):
                                    active_roles.setdefault("designer", {
                                        "canonical": "designer",
                                        "role_raw": "",
                                        "prompt": tr(f"Designing UI via {tname}", f"Đang thiết kế UI qua {tname}"),
                                        "is_heuristic": True,
                                    })
                                else:
                                    active_roles.setdefault("implementer", {
                                        "canonical": "implementer",
                                        "role_raw": "",
                                        "prompt": tr(f"Editing code via {tname}", f"Đang sửa mã qua {tname}"),
                                        "is_heuristic": True,
                                    })
                            elif tname in ("read_file", "search_web", "list_resources"):
                                active_roles.setdefault("searcher", {
                                    "canonical": "searcher",
                                    "role_raw": "",
                                    "prompt": tr(f"Researching codebase via {tname}", f"Đang đọc mã/tài liệu qua {tname}"),
                                    "is_heuristic": True,
                                })
                            elif tname == "run_command":
                                cmd_str = str(args_obj.get("CommandLine", ""))
                                if cmd_str.strip().startswith("git ") or " git " in cmd_str:
                                    active_roles.setdefault("committer", {
                                        "canonical": "committer",
                                        "role_raw": "",
                                        "prompt": tr("Executing git command", "Đang chạy lệnh git"),
                                        "is_heuristic": True,
                                    })
                                elif any(k in cmd_str for k in ("pytest", "python -m unittest", "cargo test", "npm test")):
                                    active_roles.setdefault("implementer", {
                                        "canonical": "implementer",
                                        "role_raw": "",
                                        "prompt": tr("Running tests/verification", "Đang chạy test kiểm định"),
                                        "is_heuristic": True,
                                    })
                                else:
                                    active_roles.setdefault("orchestrator", {
                                        "canonical": "orchestrator",
                                        "role_raw": "",
                                        "prompt": tr("Executing system command", "Đang điều phối lệnh hệ thống"),
                                        "is_heuristic": True,
                                    })
                            elif tname == "ask_question":
                                active_roles.setdefault("lead-architect", {
                                    "canonical": "lead-architect",
                                    "role_raw": "",
                                    "prompt": tr("Clarifying architecture with user", "Đang làm rõ kiến trúc với người dùng"),
                                    "is_heuristic": True,
                                })
            except Exception:
                pass

            task_items: Dict[str, Any] = {"running": [], "pending": [], "done": []}
            task_md = conv_dir / "task.md"
            if task_md.exists():
                try:
                    t_lines = task_md.read_text(encoding="utf-8", errors="ignore").splitlines()
                    task_items["running"] = [l.strip() for l in t_lines if "[/]" in l]
                    task_items["pending"] = [l.strip() for l in t_lines if "[ ]" in l]
                    task_items["done"] = [l.strip() for l in t_lines if "[x]" in l or "[X]" in l]
                except Exception:
                    pass

            recent_sessions.append(
                {
                    "id": conv_dir.name,
                    "age_sec": age_sec,
                    "steps": len(lines),
                    "last_tool": last_tool,
                    "subagents": subagents_invoked,
                    "tasks": task_items,
                }
            )

    return active_roles, recent_sessions


def render_ps_view(target_dir: Path, active_arg: str = "") -> str:
    """Render the full PS monitor view as a string."""
    project_path = target_dir.resolve()
    lines: List[str] = []

    header = c(
        tr(
            f"🛰️  Live Multi-Agent & OS Process Monitor — {project_path.name} ({project_path})",
            f"🛰️  Giám Sát Tiến Trình OS & Đội Ngũ Multi-Agent — {project_path.name} ({project_path})",
        ),
        BOLD + GREEN,
    )
    lines.append(header)

    # Detect live occupancy and sessions
    active_roles, recent_sessions = detect_live_agent_occupancy(project_path, manual_active=active_arg)
    resolved_theme = detect_system_theme()
    active_accent = (rgb_fg(LIGHT_ACTIVE_BADGE_RGB) or YELLOW) if resolved_theme == "light" else YELLOW

    # 1. 8-Column Mascot Pixel Art with Glow
    grid_art = render_7col_agent_ps_grid(active_roles, theme=resolved_theme)
    lines.append(grid_art)

    # Active Task Occupancy Breakdown
    if active_roles:
        lines.append(
            c(
                tr(
                    f"  ⚡ Active Task Occupancy ({len(active_roles)} role(s) occupying tasks):",
                    f"  ⚡ Tác Vụ Đang Chiếm Giữ ({len(active_roles)} vai trò đang hoạt động):",
                ),
                BOLD + active_accent,
            )
        )
        for r_id in [r[0] for r in PIXEL_ART_ANIMALS]:
            if r_id in active_roles:
                emoji = MASCOT_EMOJIS.get(r_id, "🤖")
                info = active_roles[r_id]
                desc = format_active_role_desc(r_id, info, lang=CURRENT_LANG)
                boost_c = _mascot_role_rgb(r_id, resolved_theme, active_boost=True)
                role_lbl = f"{BOLD}{rgb_fg(boost_c)}[{r_id}]{RESET}"
                kind_name = ROLE_ANIMALS_VI.get(r_id, "linh vật") if CURRENT_LANG == "vi" else ROLE_ANIMALS.get(r_id, "mascot")
                kind_lbl = f"({kind_name})"
                lines.append(f"     • {emoji} {role_lbl} {kind_lbl:<12} : {c(desc, active_accent)}")
    else:
        lines.append(
            f"  {c(tr('○ Standby: All 8 mascots are idle. No background subagents currently occupying tasks.', '○ Chờ lệnh: Cả 8 linh vật đang nghỉ. Chưa có subagent nào chiếm giữ tác vụ.'), DIM)}"
        )
    lines.append("")

    # 2. Live OS Processes from /proc
    lines.append(
        c(
            tr(
                "  🖥️  OS Processes:",
                "  🖥️  Tiến trình OS:",
            ),
            BOLD + CYAN,
        )
    )
    running_procs = get_live_os_procs(project_path)
    if running_procs:
        # Table Header
        hdr_line = (
            _col("PID", 8, BOLD)
            + _col("COMM", 10, BOLD)
            + _col("STATE", 14, BOLD)
            + _col("RAM (RSS)", 12, BOLD)
            + _col("THREADS", 9, BOLD)
            + _col("UPTIME", 10, BOLD)
            + _col("CWD / PROJECT", 30, BOLD)
        )
        lines.append(f"     {hdr_line}")
        lines.append(f"     {DIM}{'─' * 8}{'─' * 10}{'─' * 14}{'─' * 12}{'─' * 9}{'─' * 10}{'─' * 35}{RESET}")
        for p in running_procs:
            proj_tag = (
                c(tr(" [THIS PROJECT]", " [PROJECT NÀY]"), BOLD + GREEN)
                if p["in_project"]
                else ""
            )
            comm_color = BOLD + MAGENTA if p["comm"] in ("agy", "codex", "claude") else BOLD + CYAN
            row_str = (
                _col(p["pid"], 8)
                + _col(p["comm"], 10, comm_color)
                + _col(p["state"], 14)
                + _col(p["vmrss"], 12, YELLOW)
                + _col(p["threads"], 9)
                + _col(p["elapsed"], 10)
                + _col(p["cwd"] + proj_tag, 35, CYAN if not p["in_project"] else "")
            )
            lines.append(f"     {row_str}")
    else:
        lines.append(
            f"     {c(tr('No active agy / codex / claude processes detected in /proc.', 'Không phát hiện tiến trình agy / codex / claude nào trong /proc.'), DIM)}"
        )

    # 3. Active Antigravity Sessions, Subagents & Checklist Tasks
    lines.append(
        c(
            tr(
                "\n  💬  Agent Sessions:",
                "\n  💬  Phiên làm việc:",
            ),
            BOLD + CYAN,
        )
    )
    if recent_sessions:
        for s in recent_sessions[:3]:
            age_sec = s["age_sec"]
            if age_sec < 120:
                state_str = c(tr("● ACTIVE NOW", "● ĐANG HOẠT ĐỘNG"), BOLD + GREEN)
            elif age_sec < 3600:
                state_str = c(tr(f"◐ Idle ({age_sec // 60}m ago)", f"◐ Nghỉ ({age_sec // 60} phút trước)"), YELLOW)
            else:
                state_str = c(tr(f"○ Inactive ({age_sec // 3600}h ago)", f"○ Cũ ({age_sec // 3600} giờ trước)"), DIM)

            lines.append(
                f"     • {BOLD}Session {s['id'][:8]}…{RESET} [{state_str}] "
                f"— {tr('steps', 'bước')}: {s['steps']} | {tr('last tool', 'tool gần nhất')}: {c(s['last_tool'], CYAN)}"
            )
            if s["subagents"]:
                for sa in s["subagents"][-3:]:
                    sa_type = sa['type']
                    sa_canonical = ROLE_ALIASES.get(sa_type, sa_type)
                    sa_role_title = ROLE_DESCRIPTIONS_VI.get(sa_canonical, sa['role']) if CURRENT_LANG == "vi" else ROLE_DESCRIPTIONS_EN.get(sa_canonical, sa['role'])
                    p_disp = sa['prompt']
                    if CURRENT_LANG == "en" and _is_vi_text(p_disp):
                        p_disp = ROLE_TASK_DEFAULT_EN.get(sa_canonical, "Executing subagent task")
                        lines.append(
                            f"       ↳ 🤖 {c(sa['type'], BOLD + MAGENTA)} ({sa_role_title}): {p_disp}"
                        )
                    else:
                        lines.append(
                            f"       ↳ 🤖 {c(sa['type'], BOLD + MAGENTA)} ({sa_role_title}): \"{p_disp}…\""
                        )
            else:
                lines.append(
                    f"       ↳ {c(tr('Main agent executing directly (no subagents spawned in recent steps).', 'Main agent đang xử lý trực tiếp (chưa gọi subagent ở các bước gần đây).'), DIM)}"
                )

            t = s["tasks"]
            if t["running"] or t["pending"] or t["done"]:
                lines.append(
                    f"       ↳ 📋 {tr('Checklist', 'Tiến độ task.md')}: "
                    f"{c(str(len(t['running'])) + tr(' running', ' đang chạy'), YELLOW)} | "
                    f"{c(str(len(t['pending'])) + tr(' pending', ' chờ'), CYAN)} | "
                    f"{c(str(len(t['done'])) + tr(' done', ' xong'), GREEN)}"
                )
                for ip in t["running"][:3]:
                    lines.append(f"          ⚡ {c(ip, BOLD + YELLOW)}")
    else:
        lines.append(
            f"     {c(tr('No Antigravity session transcripts found.', 'Không tìm thấy lịch sử phiên Antigravity nào.'), DIM)}"
        )

    # 4. Workspace Agent Readiness (.agents/agents/*/agent.md)
    lines.append(
        c(
            tr(
                "\n  👥  Workspace Agents:",
                "\n  👥  Trạng thái Agents:",
            ),
            BOLD + CYAN,
        )
    )
    agents_dir = project_path / ".agents" / "agents"
    valid_tiers = {"pro", "flash", "flash_lite", "inherit"}
    if agents_dir.is_dir():
        found_any = False
        for role_dir in sorted(agents_dir.iterdir()):
            md_path = role_dir / "agent.md"
            toml_path = role_dir / "agent.toml"
            if not md_path.exists():
                continue
            found_any = True
            fm = parse_yaml_frontmatter(md_path)
            model_val = fm.get("model", "inherit")
            main_ag = fm.get("mainAgent", "")
            sub_ag = fm.get("subagent", "")
            is_valid = model_val in valid_tiers
            status_badge = (
                c(tr("✔ Ready in /agents", "✔ Sẵn sàng trong /agents"), GREEN)
                if is_valid and main_ag == "true"
                else (
                    c(tr("✔ Valid subagent", "✔ Subagent hợp lệ"), GREEN)
                    if is_valid
                    else c(
                        tr(
                            f"✖ Invalid model '{model_val}' (run `agt init` to fix)",
                            f"✖ Model '{model_val}' không hợp lệ (chạy `agt init` để sửa)",
                        ),
                        RED,
                    )
                )
            )
            codex_badge = c("codex ✔", CYAN) if toml_path.exists() else c("codex -", DIM)
            emoji = MASCOT_EMOJIS.get(role_dir.name, "•")
            lines.append(
                f"     {emoji} [{BOLD}{role_dir.name:<12}{RESET}] "
                f"tier={c(model_val, YELLOW)} | main={main_ag or 'false'} | sub={sub_ag or 'false'} "
                f"| {codex_badge} -> {status_badge}"
            )
        if not found_any:
            lines.append(
                f"     {c(tr('No agent.md files found in .agents/agents/.', 'Chưa có file agent.md trong .agents/agents/.'), YELLOW)}"
            )
    else:
        lines.append(
            f"     {c(tr('No .agents/agents/ directory found in this project.', 'Chưa có thư mục .agents/agents/ tại project này.'), YELLOW)}"
        )

    return "\n".join(lines)


def _read_terminal_key(timeout: float = 0.05) -> str:
    """Read a single keypress or escape sequence (arrows, mouse wheel, etc.)."""
    import select

    try:
        r, _, _ = select.select([sys.stdin], [], [], timeout)
    except (InterruptedError, OSError):
        return ""
    if not r:
        return ""
    try:
        ch = sys.stdin.read(1)
    except Exception:
        return ""
    if not ch or ch != "\x1b":
        return ch

    # Handle ANSI escape sequence
    try:
        r2, _, _ = select.select([sys.stdin], [], [], 0.03)
        if not r2:
            return "\x1b"
        ch2 = sys.stdin.read(1)
        if ch2 == "[":
            buf = ""
            while True:
                r3, _, _ = select.select([sys.stdin], [], [], 0.01)
                if not r3:
                    break
                c_sub = sys.stdin.read(1)
                buf += c_sub
                if c_sub in ("M", "m", "~", "A", "B", "C", "D", "H", "F"):
                    break
            full_seq = ch2 + buf
            # SGR Mouse wheel events
            if full_seq.startswith("[<64;") and full_seq.endswith("M"):
                return "WHEEL_UP"
            elif full_seq.startswith("[<65;") and full_seq.endswith("M"):
                return "WHEEL_DOWN"
            elif full_seq == "[A":
                return "UP"
            elif full_seq == "[B":
                return "DOWN"
            elif full_seq == "[C":
                return "RIGHT"
            elif full_seq == "[D":
                return "LEFT"
            elif full_seq.startswith("[5"):
                return "PAGE_UP"
            elif full_seq.startswith("[6"):
                return "PAGE_DOWN"
            elif full_seq.startswith("[H") or full_seq.startswith("[1"):
                return "HOME"
            elif full_seq.startswith("[F") or full_seq.startswith("[4"):
                return "END"
            return full_seq
        elif ch2 == "O":
            ch3 = sys.stdin.read(1)
            if ch3 == "A":
                return "UP"
            elif ch3 == "B":
                return "DOWN"
            elif ch3 == "H":
                return "HOME"
            elif ch3 == "F":
                return "END"
            return ch2 + ch3
        return ch2
    except Exception:
        return ch


def cmd_ps(
    target_dir: Path,
    active_arg: str = "",
    watch: Optional[bool] = None,
    interval: float = 2.0,
) -> None:
    """
    Live Multi-Agent & OS Process Monitor.
    Runs continuously like `top`/`htop` when run interactively, with nvim-style scrolling (j/k/d/u/g/G),
    until user presses 'q' or Ctrl+C.
    Can be run once with `--once` / `-1` or if not attached to a TTY.
    """
    project_path = target_dir.resolve()
    is_interactive = sys.stdin.isatty() and sys.stdout.isatty()
    if watch is None:
        watch = is_interactive

    if not watch or not is_interactive:
        view = render_ps_view(project_path, active_arg=active_arg)
        print(f"\n{view}")
        print(
            c(
                tr(
                    "\n  💡 Tips inside your coding tool:",
                    "\n  💡 Mẹo kiểm tra trực tiếp bên trong công cụ:",
                ),
                BOLD + YELLOW,
            )
        )
        print(
            tr(
                f"     • Inside {BOLD}agy{RESET}  : Type {c('/agents', GREEN)} to switch/view workspace agents (or press {c('k', YELLOW)} to kill a running subagent), and {c('/tasks', GREEN)} for background tasks.\n"
                f"     • Inside {BOLD}shell{RESET}: Run {c('agt ps', GREEN)} for live continuous top monitor (nvim keys {c('j/k', GREEN)}, press {c('q', YELLOW)} to quit), or {c('agt ps --once', GREEN)} for single snapshot.",
                f"     • Trong {BOLD}agy{RESET}     : Gõ {c('/agents', GREEN)} để xem/chuyển đổi agents (nhấn {c('k', YELLOW)} để dừng subagent đang chạy), và {c('/tasks', GREEN)} để xem tác vụ nền.\n"
                f"     • Ngoài {BOLD}terminal{RESET}: Gõ {c('agt ps', GREEN)} để theo dõi liên tục như top (cuộn phím {c('j/k', GREEN)}, nhấn {c('q', YELLOW)} để thoát), hoặc {c('agt ps --once', GREEN)} để in 1 lần.",
            )
        )
        return

    try:
        import termios
        import tty
    except ImportError:
        view = render_ps_view(project_path, active_arg=active_arg)
        print(f"\n{view}")
        return

    fd = sys.stdin.fileno()
    try:
        old_settings = termios.tcgetattr(fd)
    except Exception:
        view = render_ps_view(project_path, active_arg=active_arg)
        print(f"\n{view}")
        return

    all_lines: List[str] = []
    last_fetch_time = 0.0
    scroll_offset = 0
    paused = False
    cur_interval = max(0.5, float(interval))

    # Switch to alternate screen buffer, hide cursor, and enable SGR mouse tracking
    sys.stdout.write("\033[?1049h\033[?25l\033[?1000h\033[?1006h")
    sys.stdout.flush()

    try:
        tty.setcbreak(fd)
        while True:
            now = time.time()
            # 1. Fetch fresh telemetry data if interval expired or first run
            if not all_lines or (not paused and (now - last_fetch_time >= cur_interval)):
                view = render_ps_view(project_path, active_arg=active_arg)
                all_lines = view.splitlines()
                last_fetch_time = now

            # 2. Viewport calculation with nvim-like scroll offset
            term_size = shutil.get_terminal_size((115, 24))
            term_h, term_w = term_size.lines, term_size.columns
            content_height = max(1, term_h - 2)
            total_lines = len(all_lines)
            max_scroll = max(0, total_lines - content_height)
            scroll_offset = max(0, min(max_scroll, scroll_offset))

            visible_lines = all_lines[scroll_offset : scroll_offset + content_height]

            # 3. Clear alternate screen and write visible viewport
            sys.stdout.write("\033[H\033[2J")
            for vl in visible_lines:
                sys.stdout.write(vl + "\n")
            if len(visible_lines) < content_height:
                sys.stdout.write("\n" * (content_height - len(visible_lines)))

            # 4. Divider and nvim-style scroll footer bar
            sys.stdout.write(DIM + "─" * term_w + RESET + "\n")
            now_str = datetime.now().strftime("%H:%M:%S")
            pause_badge = f"{BOLD}{YELLOW}[PAUSED] {RESET}" if paused else ""

            if total_lines <= content_height:
                scroll_info = tr("[All]", "[Tất cả]")
            else:
                pct = int((scroll_offset / max_scroll) * 100) if max_scroll > 0 else 0
                scroll_info = f"[{scroll_offset + 1}-{min(total_lines, scroll_offset + content_height)}/{total_lines} ({pct}%)]"

            if term_w >= 105:
                footer_text = tr(
                    f"  {pause_badge}[q] Quit  [j/k] Scroll  [d/u] Half-page  [g/G] Top/Bot  [r] Refresh  [space] {'Resume' if paused else 'Pause'}  [+/-] ({cur_interval:.1f}s)  •  {scroll_info}  •  {now_str}",
                    f"  {pause_badge}[q] Thoát  [j/k] Cuộn  [d/u] Nửa trang  [g/G] Đầu/Cuối  [r] Làm mới  [space] {'Tiếp tục' if paused else 'Tạm dừng'}  [+/-] ({cur_interval:.1f}s)  •  {scroll_info}  •  {now_str}",
                )
            elif term_w >= 80:
                footer_text = tr(
                    f"  {pause_badge}[q] Quit  [j/k] Scroll  [d/u] Half-pg  [space] Pause  [+/-] ({cur_interval:.1f}s)  •  {scroll_info}  •  {now_str}",
                    f"  {pause_badge}[q] Thoát  [j/k] Cuộn  [d/u] Nửa trang  [space] Tạm dừng  [+/-] ({cur_interval:.1f}s)  •  {scroll_info}  •  {now_str}",
                )
            else:
                footer_text = tr(
                    f"  {pause_badge}[q] Quit  [j/k] {scroll_info}  •  {now_str}",
                    f"  {pause_badge}[q] Thoát  [j/k] {scroll_info}  •  {now_str}",
                )
            sys.stdout.write(footer_text[:term_w] + "\n")
            sys.stdout.flush()

            # 5. Wait for keypress or interval timeout
            time_until_refresh = max(0.05, cur_interval - (time.time() - last_fetch_time)) if not paused else 0.5
            key = _read_terminal_key(timeout=min(0.2, time_until_refresh))
            if not key:
                continue

            if key in ("q", "Q", "\x03"):  # 'q' or Ctrl+C
                return
            elif key in ("j", "DOWN", "\x05"):  # scroll down 1 line (nvim j / Down / Ctrl+E)
                scroll_offset = min(max_scroll, scroll_offset + 1)
            elif key in ("k", "UP", "\x19"):  # scroll up 1 line (nvim k / Up / Ctrl+Y)
                scroll_offset = max(0, scroll_offset - 1)
            elif key == "WHEEL_DOWN":  # mouse wheel down
                scroll_offset = min(max_scroll, scroll_offset + 3)
            elif key == "WHEEL_UP":  # mouse wheel up
                scroll_offset = max(0, scroll_offset - 3)
            elif key in ("d", "PAGE_DOWN", "\x04"):  # half-page down (nvim d / Ctrl+D / PgDown)
                scroll_offset = min(max_scroll, scroll_offset + max(1, content_height // 2))
            elif key in ("u", "PAGE_UP", "\x15"):  # half-page up (nvim u / Ctrl+U / PgUp)
                scroll_offset = max(0, scroll_offset - max(1, content_height // 2))
            elif key in ("\x06",):  # full page down (Ctrl+F)
                scroll_offset = min(max_scroll, scroll_offset + max(1, content_height - 1))
            elif key in ("\x02",):  # full page up (Ctrl+B)
                scroll_offset = max(0, scroll_offset - max(1, content_height - 1))
            elif key in ("g", "HOME"):  # jump to top (nvim g / Home)
                scroll_offset = 0
            elif key in ("G", "END"):  # jump to bottom (nvim G / End)
                scroll_offset = max_scroll
            elif key in ("r", "R"):  # Manual instant refresh
                last_fetch_time = 0.0
            elif key == " ":  # Toggle pause
                paused = not paused
            elif key in ("+", "="):  # Faster refresh
                cur_interval = max(0.5, round(cur_interval - 0.5, 1))
            elif key in ("-", "_"):  # Slower refresh
                cur_interval = min(10.0, round(cur_interval + 0.5, 1))

    except KeyboardInterrupt:
        pass
    finally:
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except Exception:
            pass
        # Disable mouse tracking, show cursor, and leave alternate buffer
        sys.stdout.write("\033[?1000l\033[?1006l\033[?25h\033[?1049l\n")
        sys.stdout.flush()


def _apply_fallback_step_to_agent(ag: AgentSpec, step_str: str) -> str:
    """
    Apply a fallback step (e.g. 'agy:claude-opus-5-5-medium', 'agy:gemini-3.8-flash-high',
    'codex:gpt-6.1-sol (xhigh)', 'claude:sonnet') as the active model for `ag`.
    Returns a human-readable description of the activated provider/model.
    """
    raw = step_str.strip()
    provider_prefix = "agy"
    model_part = raw
    if ":" in raw:
        provider_prefix, model_part = raw.split(":", 1)
        provider_prefix = provider_prefix.strip().lower()
        model_part = model_part.strip()

    effort_match = re.search(r"\((xhigh|high|medium|low)\)", model_part)
    effort_val = effort_match.group(1) if effort_match else ""
    clean_model = re.sub(r"\s*\((xhigh|high|medium|low)\)\s*", "", model_part).strip()

    if provider_prefix == "agy":
        ag.agy_model = clean_model
        if "opus" in clean_model or "sonnet" in clean_model or "haiku" in clean_model:
            ag.claude_model = clean_model
        return f"Antigravity (agy) -> {clean_model} (tier: {_to_agy_model_tier(clean_model)})"
    if provider_prefix == "codex":
        ag.codex_model = clean_model
        if effort_val:
            ag.reasoning_effort = effort_val
        return f"OpenAI Codex (codex) -> {clean_model} ({ag.reasoning_effort})"
    if provider_prefix == "claude":
        ag.claude_model = clean_model
        return f"Claude Code (claude) -> {clean_model}"
    ag.agy_model = clean_model
    return f"Model -> {clean_model}"


def _upgrade_legacy_default_agent_fields(ag_raw: Dict, active_templates: Dict[str, Dict]) -> None:
    """Upgrade unmodified legacy default agent fields to current standard templates."""
    role_id = ag_raw.get("id", "")
    if role_id not in active_templates:
        return

    # 1. Mission and criteria upgrades for orchestrator
    if role_id == "orchestrator":
        legacy_orch_missions = {
            (
                "Receive the finalized architecture blueprint approved from the 2-round lead debate (lead-architect ⮂ lead-critic). "
                "Coordinate execution by dispatching searcher for codebase scouting, implementer for TDD coding, reviewer for independent "
                "code review, and committer for Conventional Commits. Verify overall integration without modifying production code directly."
            ),
            (
                "Tiếp nhận bản thiết kế kiến trúc hoàn thiện đã đạt đồng thuận từ cặp Lead phản biện (lead-architect ⮂ lead-critic). "
                "Điều phối thực thi phân cấp: giao searcher trinh sát mã nguồn, giao implementer viết code & test (TDD), giao reviewer "
                "kiểm định độc lập, và giao committer đóng gói git commit chuẩn. Giữ vai trò kiểm chứng tích hợp, không tự sửa code sản phẩm."
            ),
        }
        legacy_orch_criteria = {
            (
                "Zero overlapping file ownership across subagents; all reviewer findings resolved; "
                "full application builds and passes tests before claiming completion."
            ),
            (
                "Không có 2 subagent sửa cùng một file; mọi phát hiện của reviewer được xử lý triệt để; "
                "toàn bộ test suite vượt qua hoàn toàn trước khi báo cáo hoàn thành."
            ),
        }

        if ag_raw.get("mission") in legacy_orch_missions:
            ag_raw["mission"] = active_templates[role_id]["mission"]
        if ag_raw.get("goal_criteria") in legacy_orch_criteria:
            ag_raw["goal_criteria"] = active_templates[role_id]["goal_criteria"]

    # 2. Tool upgrades for any role whose agy_tools matches a known legacy default list
    legacy_tool_lists = [
        # old 8-item READ_WRITE_TOOLS
        [
            "run_command",
            "view_file",
            "write_to_file",
            "replace_file_content",
            "multi_replace_file_content",
            "grep_search",
            "find_by_name",
            "list_dir",
        ],
        # intermediate 6-item READ_WRITE_TOOLS with search_web
        [
            "run_command",
            "manage_task",
            "read_file",
            "edit_file",
            "write_file",
            "search_web",
        ],
        # intermediate 13-item READ_WRITE_TOOLS
        [
            "run_command",
            "manage_task",
            "read_file",
            "edit_file",
            "write_file",
            "search_web",
            "view_file",
            "write_to_file",
            "replace_file_content",
            "multi_replace_file_content",
            "grep_search",
            "find_by_name",
            "list_dir",
        ],
        # old 5-item / 7-item REVIEWER_TOOLS / LEAD_CRITIC_TOOLS
        [
            "view_file",
            "grep_search",
            "find_by_name",
            "list_dir",
            "run_command",
        ],
        [
            "run_command",
            "manage_task",
            "read_file",
            "view_file",
            "grep_search",
            "find_by_name",
            "list_dir",
        ],
        # old 5-item / 9-item SEARCHER_TOOLS
        [
            "view_file",
            "grep_search",
            "find_by_name",
            "search_web",
            "read_url_content",
        ],
        [
            "run_command",
            "manage_task",
            "read_file",
            "view_file",
            "grep_search",
            "find_by_name",
            "list_dir",
            "search_web",
            "read_url_content",
        ],
        # old 4-item / 7-item COMMITTER_TOOLS
        [
            "run_command",
            "view_file",
            "grep_search",
            "list_dir",
        ],
        [
            "run_command",
            "manage_task",
            "read_file",
            "view_file",
            "grep_search",
            "find_by_name",
            "list_dir",
        ],
        # old 7-item / 9-item LEAD_ARCHITECT_TOOLS
        [
            "view_file",
            "grep_search",
            "find_by_name",
            "list_dir",
            "search_web",
            "read_url_content",
            "run_command",
        ],
        [
            "run_command",
            "manage_task",
            "read_file",
            "view_file",
            "grep_search",
            "find_by_name",
            "list_dir",
            "search_web",
            "read_url_content",
        ],
        # intermediate ORCHESTRATOR_TOOLS variants
        [
            "run_command",
            "manage_task",
            "view_file",
            "grep_search",
            "find_by_name",
            "list_dir",
            "invoke_subagent",
            "send_message",
            "manage_subagents",
            "define_subagent",
        ],
        [
            "run_command",
            "manage_task",
            "read_file",
            "view_file",
            "grep_search",
            "find_by_name",
            "list_dir",
            "search_web",
            "invoke_subagent",
            "send_message",
            "manage_subagents",
            "define_subagent",
        ],
        [
            "run_command",
            "manage_task",
            "read_file",
            "search_web",
            "invoke_subagent",
            "send_message",
            "manage_subagents",
            "define_subagent",
        ],
    ]

    current_tools = ag_raw.get("agy_tools")
    if isinstance(current_tools, list):
        cur_tuple = tuple(current_tools)
        cur_sorted = tuple(sorted(current_tools))
        if any(current_tools == lt or cur_tuple == tuple(lt) or cur_sorted == tuple(sorted(lt)) for lt in legacy_tool_lists):
            ag_raw["agy_tools"] = list(active_templates[role_id]["agy_tools"])
            if role_id == "orchestrator":
                ag_raw["enable_write"] = False
        else:
            ag_raw["agy_tools"] = canonicalize_antigravity_tools(
                ag_raw["agy_tools"],
                enable_write=ag_raw.get("enable_write", True),
            )


def _load_team_config_from_disk(project_path: Path) -> Optional[TeamConfig]:
    cfg_file = project_path / ".agents" / "team-config.json"
    if not cfg_file.exists():
        return None
    try:
        raw = json.loads(cfg_file.read_text(encoding="utf-8"))
        active_templates = get_agent_templates()

        agents: List[AgentSpec] = []
        for ag_raw in raw.get("agents", []):
            role_id = ag_raw.get("id", "")
            _upgrade_legacy_default_agent_fields(ag_raw, active_templates)

            default_chain = (
                list(active_templates[role_id].get("fallback_chain", []))
                if role_id in active_templates
                else [
                    f"agy:{ag_raw.get('agy_model', 'gemini-3.8-flash-high')}",
                    f"claude:{ag_raw.get('claude_model', 'sonnet')}",
                    f"codex:{ag_raw.get('codex_model', 'gpt-6-sol')} ({ag_raw.get('reasoning_effort', 'high')})",
                ]
            )
            if not ag_raw.get("fallback_chain"):
                ag_raw["fallback_chain"] = default_chain
            agents.append(AgentSpec(**ag_raw))
        return TeamConfig(
            project_name=raw["project_name"],
            project_path=raw["project_path"],
            tech_stack=raw["tech_stack"],
            project_context=raw["project_context"],
            project_goal=raw["project_goal"],
            extra_rules=raw.get("extra_rules", []),
            harnesses=raw.get("harnesses", ["agy", "codex", "claude"]),
            skill_apply_mode=raw.get("skill_apply_mode", "symlink"),
            add_commit_restrictions=bool(raw.get("add_commit_restrictions", False)),
            selected_skill_bundles=raw.get("selected_skill_bundles", []),
            selected_skills=raw.get("selected_skills", []),
            agents=agents,
            updated_at=datetime.now().isoformat(timespec="seconds"),
        )
    except Exception:
        return None


def cmd_clean(target_dir: Path, auto_yes: bool = False, dry_run: bool = False) -> None:
    """
    Remove all AI agent configurations (.agents/, .codex/, .claude/, AGENTS.md, CLAUDE.md)
    from the target repository and reset it to clean state.
    """
    project_path = target_dir.resolve()
    print(
        c(
            tr(
                f"\n🧹 Clean AI Agent Setup — {project_path.name} ({project_path})",
                f"\n🧹 Dọn dẹp Cấu hình AI Agents — {project_path.name} ({project_path})",
            ),
            BOLD + YELLOW,
        )
    )

    items_to_clean: List[Tuple[str, Path, str]] = []

    # 1. .agents/
    agents_dir = project_path / ".agents"
    if agents_dir.exists():
        items_to_clean.append((".agents/", agents_dir, "directory"))

    # 2. .codex/config.toml
    codex_toml = project_path / ".codex" / "config.toml"
    if codex_toml.exists():
        items_to_clean.append((".codex/config.toml", codex_toml, "file"))

    # 3. .claude/agents/
    claude_agents = project_path / ".claude" / "agents"
    if claude_agents.exists():
        items_to_clean.append((".claude/agents/", claude_agents, "directory"))

    # 4. CLAUDE.md
    claude_md = project_path / "CLAUDE.md"
    if claude_md.exists():
        items_to_clean.append(("CLAUDE.md", claude_md, "file"))

    # 5. AGENTS.md
    agents_md = project_path / "AGENTS.md"
    if agents_md.exists():
        items_to_clean.append(("AGENTS.md", agents_md, "file"))

    if not items_to_clean:
        print(
            f"  {c(tr('✔ No agent configurations found in this project. Nothing to clean.', '✔ Không tìm thấy cấu hình agents nào trong project này. Không có gì để dọn dẹp.'), GREEN)}\n"
        )
        return

    print(
        c(
            tr(
                f"  Found {len(items_to_clean)} agent configuration item(s) to remove:",
                f"  Phát hiện {len(items_to_clean)} mục cấu hình agents cần xóa:",
            ),
            BOLD + CYAN,
        )
    )
    for label, p, p_type in items_to_clean:
        print(f"     • {c(label, YELLOW)} ({p_type})")

    if dry_run:
        print(
            c(
                tr(
                    "\n  [dry-run] Preview mode: No files or directories were deleted.\n",
                    "\n  [dry-run] Chế độ xem trước: Không có file hay thư mục nào bị xóa.\n",
                ),
                YELLOW,
            )
        )
        return

    if not auto_yes:
        confirm = ask_yes_no(
            tr(
                f"\n  Are you sure you want to completely remove these {len(items_to_clean)} agent item(s)?",
                f"\n  Bạn có chắc chắn muốn xóa hoàn toàn {len(items_to_clean)} mục cấu hình agents này không?",
            ),
            default=False,
        )
        if not confirm:
            print(
                c(
                    tr(
                        "  Operation aborted. No agent files were deleted.\n",
                        "  Đã hủy thao tác. Không có file nào bị xóa.\n",
                    ),
                    YELLOW,
                )
            )
            return

    # Deletion execution
    deleted_count = 0
    print()
    for label, p, p_type in items_to_clean:
        try:
            if p_type == "directory" and p.is_dir():
                shutil.rmtree(p)
            elif p.exists():
                p.unlink()
            print(f"     {c('✔', GREEN)} {tr('Removed', 'Đã xóa')}: {label}")
            deleted_count += 1
        except Exception as e:
            print(f"     {c('✖', RED)} {tr('Failed to remove', 'Lỗi khi xóa')} {label}: {e}")

    # Remove empty parent directories if any (.codex, .claude)
    for parent_name in (".codex", ".claude"):
        parent_dir = project_path / parent_name
        if parent_dir.is_dir():
            try:
                if not any(parent_dir.iterdir()):
                    parent_dir.rmdir()
                    print(f"     {c('✔', GREEN)} {tr('Removed empty directory', 'Đã xóa thư mục rỗng')}: {parent_name}/")
            except Exception:
                pass

    print(
        c(
            tr(
                f"\n✨ Successfully cleaned {deleted_count} agent configuration item(s) from {project_path.name}!\n",
                f"\n✨ Đã dọn dẹp thành công {deleted_count} mục cấu hình agents khỏi {project_path.name}!\n",
            ),
            BOLD + GREEN,
        )
    )


def cmd_fallback(
    target_dir: Path,
    role_arg: str = "",
    chain_arg: str = "",
    step_down_arg: str = "",
) -> None:
    """
    Inspect, customize, or step down along the Model & Cross-Provider Fallback Chain
    for one or all agents in a project.
    """
    project_path = target_dir.resolve()
    cfg = _load_team_config_from_disk(project_path)
    if not cfg:
        print(
            c(
                tr(
                    f"⚠️ No `.agents/team-config.json` found at {project_path}. Run `agt init` first.",
                    f"⚠️ Chưa có `.agents/team-config.json` tại {project_path}. Hãy chạy `agt init` trước.",
                ),
                YELLOW,
            )
        )
        return

    # 1. Non-interactive `--chain` update
    if chain_arg:
        normalized = chain_arg.replace("->", ",").replace("→", ",")
        new_chain = [s.strip() for s in normalized.split(",") if s.strip()]
        target_roles = [a.id for a in cfg.agents] if role_arg in ("", "all") else [role_arg]
        updated_any = False
        for ag in cfg.agents:
            if ag.id in target_roles and new_chain:
                ag.fallback_chain = list(new_chain)
                _apply_fallback_step_to_agent(ag, new_chain[0])
                updated_any = True
                print(
                    c(
                        tr(
                            f"✅ Updated fallback chain for [{ag.id}]: {format_fallback_chain(ag.fallback_chain)}",
                            f"✅ Đã cập nhật chuỗi fallback cho [{ag.id}]: {format_fallback_chain(ag.fallback_chain)}",
                        ),
                        GREEN,
                    )
                )
        if updated_any:
            cfg.updated_at = datetime.now().isoformat(timespec="seconds")
            write_project_configuration(cfg, dry_run=False)
        return

    # 2. Non-interactive `--step-down <role|all>` when primary model quota is exhausted
    if step_down_arg:
        target_roles = [a.id for a in cfg.agents] if step_down_arg == "all" else [step_down_arg]
        stepped_any = False
        for ag in cfg.agents:
            if ag.id in target_roles and len(ag.fallback_chain) >= 2:
                exhausted = ag.fallback_chain.pop(0)
                ag.fallback_chain.append(exhausted)
                next_step = ag.fallback_chain[0]
                activated_desc = _apply_fallback_step_to_agent(ag, next_step)
                stepped_any = True
                print(
                    c(
                        tr(
                            f"🔄 [{ag.id}] Stepped down from `{exhausted}` -> Activated `{next_step}` ({activated_desc})",
                            f"🔄 [{ag.id}] Đã lùi từ `{exhausted}` -> Kích hoạt `{next_step}` ({activated_desc})",
                        ),
                        BOLD + GREEN,
                    )
                )
                print(
                    f"   {tr('New chain order', 'Thứ tự chuỗi mới')}: {c(format_fallback_chain(ag.fallback_chain), YELLOW)}"
                )
        if stepped_any:
            cfg.updated_at = datetime.now().isoformat(timespec="seconds")
            write_project_configuration(cfg, dry_run=False)
        else:
            print(
                c(
                    tr(
                        f"⚠️ No matching agent with >=2 fallback steps found for '{step_down_arg}'.",
                        f"⚠️ Không tìm thấy agent phù hợp có >=2 bước fallback cho '{step_down_arg}'.",
                    ),
                    YELLOW,
                )
            )
        return

    # 3. Interactive Fallback Chain Manager
    print(
        c(
            tr(
                f"\n🔀 Model & Cross-Provider Fallback Manager — {cfg.project_name} ({project_path})",
                f"\n🔀 Quản lý Chuỗi lùi Model & Đa Provider (Fallback) — {cfg.project_name} ({project_path})",
            ),
            BOLD + GREEN,
        )
    )
    for ag in cfg.agents:
        print(
            f"  • [{BOLD}{ag.id:<12}{RESET}] "
            f"Active Agy={c(ag.agy_model, CYAN)} | Codex={c(ag.codex_model, CYAN)} ({ag.reasoning_effort})\n"
            f"    ↳ {tr('Fallback Chain', 'Chuỗi Fallback')}: {c(format_fallback_chain(ag.fallback_chain), YELLOW)}"
        )

    action_opts = [
        (
            "step-down",
            tr(
                "Step down to next fallback model (when current primary model hits quota/rate limit)",
                "Lùi xuống model dự phòng kế tiếp (khi model hiện tại hết quota / giới hạn)",
            ),
        ),
        (
            "edit-one",
            tr(
                "Configure / customize fallback chain for a specific Agent",
                "Thiết lập / tùy chỉnh chuỗi fallback cho 1 Agent cụ thể",
            ),
        ),
        (
            "edit-all",
            tr(
                "Apply a fallback chain preset across Agents",
                "Áp dụng chuỗi fallback cho toàn bộ Agents",
            ),
        ),
        (
            "exit",
            tr("Back / Exit", "Quay lại / Thoát"),
        ),
    ]
    act = ask_choice(
        tr("Select Fallback action", "Chọn thao tác với Chuỗi Fallback"),
        action_opts,
        default_index=0,
    )
    if act == "exit":
        return

    role_choices = [(ag.id, f"{ag.role} — {format_fallback_chain(ag.fallback_chain)}") for ag in cfg.agents]
    if act == "step-down":
        role_choices_with_all = [
            ("all", tr("Step down ALL agents to their next fallback model", "Lùi TẤT CẢ agents sang model dự phòng kế tiếp"))
        ] + role_choices
        chosen_role = ask_choice(
            tr("Select Agent whose current model is exhausted", "Chọn Agent đang bị hết quota model hiện tại"),
            role_choices_with_all,
            default_index=1 if len(role_choices_with_all) > 1 else 0,
        )
        cmd_fallback(project_path, step_down_arg=chosen_role)
        return

    if act == "edit-one":
        chosen_role = ask_choice(
            tr("Select Agent to customize fallback chain", "Chọn Agent muốn chỉnh chuỗi fallback"),
            role_choices,
            default_index=0,
        )
        for ag in cfg.agents:
            if ag.id == chosen_role:
                new_chain = ask_fallback_chain(ag.id, ag.fallback_chain)
                ag.fallback_chain = new_chain
                if new_chain:
                    _apply_fallback_step_to_agent(ag, new_chain[0])
                print(
                    c(
                        tr(
                            f"\n✅ Saved fallback chain for [{ag.id}]: {format_fallback_chain(ag.fallback_chain)}",
                            f"\n✅ Đã lưu chuỗi fallback cho [{ag.id}]: {format_fallback_chain(ag.fallback_chain)}",
                        ),
                        BOLD + GREEN,
                    )
                )
        cfg.updated_at = datetime.now().isoformat(timespec="seconds")
        write_project_configuration(cfg, dry_run=False)
        return

    if act == "edit-all":
        for ag in cfg.agents:
            new_chain = ask_fallback_chain(ag.id, ag.fallback_chain)
            ag.fallback_chain = new_chain
            if new_chain:
                _apply_fallback_step_to_agent(ag, new_chain[0])
        cfg.updated_at = datetime.now().isoformat(timespec="seconds")
        write_project_configuration(cfg, dry_run=False)
        print(
            c(
                tr(
                    "\n✅ Updated fallback chains and regenerated workspace agent files!",
                    "\n✅ Đã cập nhật chuỗi fallback và sinh lại các file cấu hình agent!",
                ),
                BOLD + GREEN,
            )
        )


def print_summary(cfg: TeamConfig, created_files: List[str], dry_run: bool = False) -> None:
    if CURRENT_LANG == "vi":
        prefix = "[DRY-RUN] Dự kiến tạo" if dry_run else "✅ Đã khởi tạo thành công"
        print(c(f"\n{prefix} bộ cấu hình Đội ngũ AI & Skills cho [{cfg.project_name}]!", BOLD + GREEN))
        print(f"📍 Thư mục đích: {BOLD}{cfg.project_path}{RESET}\n")
        print(c("📄 Các file cấu hình đã sinh ra:", BOLD + CYAN))
    else:
        prefix = "[DRY-RUN] Would generate" if dry_run else "✅ Successfully generated"
        print(c(f"\n{prefix} AI Team & Skills configuration for [{cfg.project_name}]!", BOLD + GREEN))
        print(f"📍 Target directory: {BOLD}{cfg.project_path}{RESET}\n")
        print(c("📄 Generated configuration files:", BOLD + CYAN))

    for f in created_files:
        rel = os.path.relpath(f, cfg.project_path) if f.startswith(cfg.project_path) else f
        print(f"   • {rel}")

    if CURRENT_LANG == "vi":
        print(c("\n🚀 Cách sử dụng ngay trong công cụ bạn đang mở:", BOLD + YELLOW))
        print(
            f"  • {BOLD}Antigravity (`agy`){RESET}   : Tự động nhận diện `.agents/agents.json`, `.agents/agents/*/agent.md`, và `.agents/skills.json`.\n"
            f"  • {BOLD}OpenAI Codex (`codex`){RESET}: Tự động nhận diện `[agents]` trong `.codex/config.toml` trỏ tới `.agents/agents/*/agent.toml`.\n"
            f"  • {BOLD}Claude Code (`claude`){RESET}: Tự động nhận diện `CLAUDE.md` và `.claude/agents/*.md`.\n"
        )
    else:
        print(c("\n🚀 How to use inside your active coding tool:", BOLD + YELLOW))
        print(
            f"  • {BOLD}Antigravity (`agy`){RESET}   : Automatically discovers `.agents/agents.json`, `.agents/agents/*/agent.md`, and `.agents/skills.json`.\n"
            f"  • {BOLD}OpenAI Codex (`codex`){RESET}: Automatically discovers `[agents]` in `.codex/config.toml` pointing to `.agents/agents/*/agent.toml`.\n"
            f"  • {BOLD}Claude Code (`claude`){RESET}: Automatically discovers `CLAUDE.md` and `.claude/agents/*.md`.\n"
        )


def print_cli_help(lang: str = "en") -> None:
    global CURRENT_LANG
    CURRENT_LANG = lang
    banner()
    if lang == "en":
        print(
            f"\n{c('USAGE:', BOLD + YELLOW)}\n"
            f"  {c('agt', BOLD + GREEN)} [command] [options]\n\n"
            f"{c('COMMANDS:', BOLD + YELLOW)}\n"
            f"  {c('(no command)', BOLD + CYAN)}  Open the interactive CLI dashboard menu (or run wizard)\n"
            f"  {c('init', BOLD + CYAN)}          Run the Multi-Agent & Skills setup wizard for a Project/Repo\n"
            f"  {c('status', BOLD + CYAN)}        Inspect active AI Team Status, 8-Role Animals & Skills\n"
            f"  {c('fallback', BOLD + CYAN)}      Configure or step down along the Model & Provider Fallback Chain\n"
            f"  {c('ps / tasks', BOLD + CYAN)}    Continuous live monitor like `top` (press `q` to quit, `--once` for snapshot)\n"
            f"  {c('clean', BOLD + CYAN)}         Clean / remove all AI agent configurations from a repo\n"
            f"  {c('list-skills', BOLD + CYAN)}   List all discovered local Skills\n\n"
            f"{c('OPTIONS:', BOLD + YELLOW)}\n"
            f"  {c('-t, --target <path>', CYAN)}     Target project directory (default: current directory)\n"
            f"  {c('-y, --yes', CYAN)}               Non-interactive mode using standard 8-agent preset\n"
            f"  {c('--clean', CYAN)}                 Clean / remove all AI agent configurations in target repo\n"
            f"  {c('--once, -1', CYAN)}              Print ps monitor snapshot once and exit (disable continuous loop)\n"
            f"  {c('--interval, -i <sec>', CYAN)}    Refresh interval in seconds for top monitor (default: 2.0)\n"
            f"  {c('--watch, -w', CYAN)}             Force continuous watch loop even in non-standard TTY\n"
            f"  {c('--active, -a <roles>', CYAN)}    Manually specify active role(s) to simulate glowing mascots\n"
            f"  {c('--goal <text>', CYAN)}           Primary project goal (used with --yes)\n"
            f"  {c('--context <text>', CYAN)}        Project context description (used with --yes)\n"
            f"  {c('--harnesses <list>', CYAN)}      Target harnesses: agy,codex,claude (default: all)\n"
            f"  {c('--skill-mode <mode>', CYAN)}     Skill linking mode: symlink | copy | json-only\n"
            f"  {c('--step-down <role|all>', CYAN)}  Promote next fallback model when current model hits quota (`agt fallback`)\n"
            f"  {c('--role <role>', CYAN)}           Target role for `agt fallback --chain`\n"
            f"  {c('--chain <list>', CYAN)}          Set custom fallback chain (comma or '->' separated)\n"
            f"  {c('--lang <en|vi>', CYAN)}          CLI display language: en (English, default) or vi (Tiếng Việt)\n"
            f"  {c('--dry-run', CYAN)}               Preview generated files without writing to disk\n"
            f"  {c('-h, --help', CYAN)}              Show this help message\n\n"
            f"{c('EXAMPLES:', BOLD + YELLOW)}\n"
            f"  • Launch interactive setup in a project      : {c('cd ~/project-example && agt', GREEN)}\n"
            f"  • Configure / manage model fallback chains   : {c('agt fallback -t ~/project-example', GREEN)}\n"
            f"  • Step down to next fallback model on quota  : {c('agt fallback -t ~/project-example --step-down orchestrator', GREEN)}\n"
            f"  • Check running agents & active tasks        : {c('agt ps -t ~/project-example', GREEN)}\n"
            f"  • Quick preset init for a repository         : {c('agt init -t ~/project-example -y', GREEN)}\n"
            f"  • Inspect AI team status                     : {c('agt status -t ~/project-example', GREEN)}\n"
        )
    else:
        print(
            f"\n{c('CÁCH SỬ DỤNG:', BOLD + YELLOW)}\n"
            f"  {c('agt', BOLD + GREEN)} [lệnh] [tùy chọn]\n\n"
            f"{c('CÁC LỆNH CHÍNH:', BOLD + YELLOW)}\n"
            f"  {c('(không truyền lệnh)', BOLD + CYAN)} Mở Bảng điều khiển tương tác (TUI Menu / Wizard)\n"
            f"  {c('init', BOLD + CYAN)}                Chạy Wizard thiết lập đội ngũ AI & Skills cho Project/Repo\n"
            f"  {c('status', BOLD + CYAN)}              Xem trạng thái Đội ngũ AI, 8 Linh vật & Skills\n"
            f"  {c('fallback', BOLD + CYAN)}            Thiết lập hoặc lùi Model theo Chuỗi Fallback đa Provider\n"
            f"  {c('ps / tasks', BOLD + CYAN)}          Giám sát liên tục như `top` (bấm `q` để thoát, `--once` để in 1 lần)\n"
            f"  {c('clean', BOLD + CYAN)}               Dọn dẹp / xóa toàn bộ cấu hình AI Agents khỏi repo\n"
            f"  {c('list-skills', BOLD + CYAN)}         Liệt kê toàn bộ 150+ Skills đang có trên máy\n\n"
            f"{c('TÙY CHỌN (OPTIONS):', BOLD + YELLOW)}\n"
            f"  {c('-t, --target <path>', CYAN)}     Đường dẫn tới project/repo cần thiết lập (mặc định: `.`)\n"
            f"  {c('-y, --yes', CYAN)}               Khởi tạo tự động bằng Preset 8 Agents chuẩn (không hỏi đáp)\n"
            f"  {c('--clean', CYAN)}                 Dọn dẹp / xóa toàn bộ cấu hình AI Agents trong repo chỉ định\n"
            f"  {c('--once, -1', CYAN)}              In ảnh chụp trạng thái 1 lần rồi thoát (tắt vòng lặp như `top`)\n"
            f"  {c('--interval, -i <sec>', CYAN)}    Chu kỳ làm mới màn hình theo dõi (mặc định: 2.0 giây)\n"
            f"  {c('--watch, -w', CYAN)}             Bắt buộc chạy vòng lặp theo dõi liên tục\n"
            f"  {c('--active, -a <roles>', CYAN)}    Chỉ định vai trò đang chiếm task để linh vật phát sáng\n"
            f"  {c('--goal <text>', CYAN)}           Mục tiêu chính của project (dùng kèm `--yes`)\n"
            f"  {c('--context <text>', CYAN)}        Ngữ cảnh kiến trúc của project (dùng kèm `--yes`)\n"
            f"  {c('--harnesses <list>', CYAN)}      Công cụ xuất cấu hình: `agy,codex,claude` (mặc định: cả 3)\n"
            f"  {c('--skill-mode <mode>', CYAN)}     Chế độ gắn skills: `symlink` | `copy` | `json-only`\n"
            f"  {c('--step-down <role|all>', CYAN)}  Lùi ngay sang model dự phòng kế tiếp khi hết quota (`agt fallback`)\n"
            f"  {c('--role <role>', CYAN)}           Chọn role cần gán chuỗi fallback (`agt fallback --chain`)\n"
            f"  {c('--chain <list>', CYAN)}          Chuỗi fallback tùy chỉnh (cách nhau dấu phẩy hoặc `->`)\n"
            f"  {c('--lang <en|vi>', CYAN)}          Ngôn ngữ giao diện CLI: `en` (Tiếng Anh, mặc định) hoặc `vi` (Tiếng Việt)\n"
            f"  {c('--dry-run', CYAN)}               Xem trước danh sách file sẽ sinh ra mà không ghi xuống ổ cứng\n"
            f"  {c('-h, --help', CYAN)}              Hiển thị bảng hướng dẫn này\n\n"
            f"{c('VÍ DỤ:', BOLD + YELLOW)}\n"
            f"  • Thiết lập đội AI cho một project       : {c('cd ~/project-example && agt', GREEN)}\n"
            f"  • Quản lý / đổi chuỗi lùi Fallback       : {c('agt fallback -t ~/project-example --lang vi', GREEN)}\n"
            f"  • Lùi model ngay khi Argon hết quota     : {c('agt fallback -t ~/project-example --step-down orchestrator', GREEN)}\n"
            f"  • Kiểm tra agents & tasks đang chạy      : {c('agt ps -t ~/project-example --lang vi', GREEN)}\n"
            f"  • Tạo nhanh đội AI bằng Preset           : {c('agt init -t ~/project-example -y', GREEN)}\n"
            f"  • Kiểm tra trạng thái đội AI             : {c('agt status -t ~/project-example', GREEN)}\n"
        )


def run_interactive_dashboard(target_path: Path, projects_root: Path, lang: str = "en") -> None:
    """Interactive CLI Dashboard (defaults to English, toggleable to Vietnamese)."""
    global CURRENT_LANG
    CURRENT_LANG = lang
    while True:
        banner()
        cwd_str = str(target_path.resolve())
        if CURRENT_LANG == "vi":
            print(f"📍 Thư mục làm việc hiện tại: {c(cwd_str, BOLD + GREEN)}")
            menu_opts = [
                ("wizard", "Thiết lập đội ngũ AI & Skills theo từng bước (Interactive Wizard)"),
                ("preset", "Khởi tạo nhanh Đội ngũ Multi-Agent 2 Pha (Lead Phản biện + Thực thi)"),
                ("status", "Xem trạng thái Đội ngũ AI, 8 Linh vật & Skills (`agt status`)"),
                ("fallback", "Thiết lập / Lùi Model theo Chuỗi Fallback đa Provider (`agt fallback`)"),
                ("ps", "Kiểm tra Agents nào đang chạy task nào (Live Agent & Task Monitor)"),
                ("clean", "Dọn dẹp / Xóa toàn bộ cấu hình AI Agents trong repo (`agt clean`)"),
                ("list-skills", "Tra cứu danh sách 150+ Skills đang có trên máy"),
                ("lang", "Switch CLI language to English (Chuyển sang Tiếng Anh)"),
                ("exit", "Thoát (Exit)"),
            ]
            prompt_title = "BẢNG ĐIỀU KHIỂN CHÍNH — Chọn tác vụ bạn muốn thực hiện"
        else:
            print(f"📍 Current working directory: {c(cwd_str, BOLD + GREEN)}")
            menu_opts = [
                ("wizard", "Configure Multi-Agent Team & Skills step-by-step (Interactive Wizard)"),
                ("preset", "Quick-initialize 2-Phase Multi-Agent Team (Lead Debate + Execution)"),
                ("status", "Inspect active AI Team Status, 8-Role Animals & Skills (`agt status`)"),
                ("fallback", "Configure or Step Down Model & Provider Fallback Chains (`agt fallback`)"),
                ("ps", "Check live running Agents, subagents & active tasks (`agt ps`)"),
                ("clean", "Clean / Remove all AI agent configurations from repo (`agt clean`)"),
                ("list-skills", "Browse all 150+ discovered local Skills"),
                ("lang", "Chuyển ngôn ngữ giao diện sang Tiếng Việt (Switch to Vietnamese)"),
                ("exit", "Exit"),
            ]
            prompt_title = "MAIN DASHBOARD — Select an action"

        action = ask_choice(prompt_title, menu_opts, default_index=0)
        if action == "exit":
            print(c("\n👋 Tạm biệt! Chúc bạn code hiệu quả cùng đội ngũ AI." if CURRENT_LANG == "vi" else "\n👋 Goodbye!", CYAN))
            return
        if action == "lang":
            CURRENT_LANG = "en" if CURRENT_LANG == "vi" else "vi"
            continue
        if action == "list-skills":
            cmd_list_skills()
            return
        if action == "status":
            proj = select_project_directory(target_path, projects_root)
            cmd_status(proj)
            return
        if action == "fallback":
            proj = select_project_directory(target_path, projects_root)
            cmd_fallback(proj)
            return
        if action == "ps":
            proj = select_project_directory(target_path, projects_root)
            cmd_ps(proj)
            return
        if action == "clean":
            proj = select_project_directory(target_path, projects_root)
            cmd_clean(proj, auto_yes=False, dry_run=False)
            return
        if action == "preset":
            proj = select_project_directory(target_path, projects_root)
            default_goal = (
                f"Phát triển, kiểm thử và duy trì {proj.name} với mô hình 2 pha: lead phản biện & đội thực thi."
                if CURRENT_LANG == "vi"
                else f"Develop, test, and maintain {proj.name} with 2-phase lead debate & execution team."
            )
            goal = ask_text(
                "Nhập mục tiêu chính của Project (Goal)" if CURRENT_LANG == "vi" else "Enter primary project goal",
                default_goal,
            )
            cfg = build_preset_config(
                target_dir=proj,
                goal=goal,
                context="",
                harnesses=["agy", "codex", "claude"],
                bundles=["core-subagents-tdd", "ponytail-lean", "agy-swarm"],
                skill_apply_mode="symlink",
            )
            created = write_project_configuration(cfg, dry_run=False)
            print_summary(cfg, created, dry_run=False)
            return
        if action == "wizard":
            cfg = run_interactive_wizard(target_path, projects_root, show_banner=False)
            created = write_project_configuration(cfg, dry_run=False)
            print_summary(cfg, created, dry_run=False)
            return


def build_cli_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for agt CLI."""
    parser = argparse.ArgumentParser(
        prog="agt",
        add_help=False,
        description="CLI Wizard (agt) to configure Multi-Agent teams & Skills for ~/Projects.",
    )
    parser.add_argument("--lang", type=str, default="en", choices=["en", "vi"], help="CLI language (en/vi)")
    parser.add_argument("--target", "-t", type=str, default=".", help="Target project/repo path")
    parser.add_argument("--yes", "-y", action="store_true", help="Non-interactive mode with standard preset")
    parser.add_argument("--active", "-a", type=str, default="", help="Active role(s) to simulate/highlight in ps monitor (comma-separated)")
    parser.add_argument("--once", "-1", action="store_true", help="Print snapshot once and exit (disable continuous top monitor)")
    parser.add_argument("--interval", "-i", type=float, default=2.0, help="Refresh interval in seconds for top monitor (default: 2.0)")
    parser.add_argument("--watch", "-w", action="store_true", help="Force continuous watch loop even in non-standard TTY")
    parser.add_argument("--clean", action="store_true", help="Remove all AI agent configurations in target repo")
    parser.add_argument("--dry-run", action="store_true", help="Preview generated files without writing")
    subparsers = parser.add_subparsers(dest="command")

    p_init = subparsers.add_parser("init", add_help=False, help="Run the Multi-Agent setup wizard")
    p_init.add_argument("--lang", type=str, default=argparse.SUPPRESS, choices=["en", "vi"])
    p_init.add_argument("--target", "-t", type=str, default=argparse.SUPPRESS, help="Target project/repo path")
    p_init.add_argument("--yes", "-y", action="store_true", default=argparse.SUPPRESS, help="Non-interactive mode with standard preset")
    p_init.add_argument("--goal", type=str, default="", help="Primary project goal (used with --yes)")
    p_init.add_argument("--context", type=str, default="", help="Project context (used with --yes)")
    p_init.add_argument(
        "--harnesses",
        type=str,
        default="agy,codex,claude",
        help="Target harnesses: agy,codex,claude",
    )
    p_init.add_argument(
        "--bundles",
        type=str,
        default="core-subagents-tdd,ponytail-lean,agy-swarm",
        help="Comma-separated skill bundles to attach",
    )
    p_init.add_argument(
        "--skill-mode",
        type=str,
        default="symlink",
        choices=["symlink", "copy", "json-only"],
        help="Skill linking mode (symlink, copy, json-only)",
    )
    p_init.add_argument("--dry-run", action="store_true", default=argparse.SUPPRESS, help="Preview generated files without writing")

    p_list = subparsers.add_parser("list-skills", add_help=False, help="List all discovered local Skills")
    p_list.add_argument("--lang", type=str, default=argparse.SUPPRESS, choices=["en", "vi"])

    p_status = subparsers.add_parser("status", add_help=False, help="Inspect active AI Team status for a Project")
    p_status.add_argument("--lang", type=str, default=argparse.SUPPRESS, choices=["en", "vi"])
    p_status.add_argument("--target", "-t", type=str, default=argparse.SUPPRESS, help="Target project/repo path")

    p_ps = subparsers.add_parser("ps", add_help=False, help="Continuous live monitor like `top` (press `q` to quit, `--once` for snapshot)")
    p_ps.add_argument("--lang", type=str, default=argparse.SUPPRESS, choices=["en", "vi"])
    p_ps.add_argument("--target", "-t", type=str, default=argparse.SUPPRESS, help="Target project/repo path")
    p_ps.add_argument("--active", "-a", type=str, default=argparse.SUPPRESS, help="Active role(s) to highlight (comma-separated)")
    p_ps.add_argument("--once", "-1", action="store_true", default=argparse.SUPPRESS, help="Print snapshot once and exit")
    p_ps.add_argument("--interval", "-i", type=float, default=argparse.SUPPRESS, help="Refresh interval in seconds (default: 2.0)")
    p_ps.add_argument("--watch", "-w", action="store_true", default=argparse.SUPPRESS, help="Force continuous watch loop")

    p_tasks = subparsers.add_parser("tasks", add_help=False, help="Alias for `ps` — continuous live monitor like `top`")
    p_tasks.add_argument("--lang", type=str, default=argparse.SUPPRESS, choices=["en", "vi"])
    p_tasks.add_argument("--target", "-t", type=str, default=argparse.SUPPRESS, help="Target project/repo path")
    p_tasks.add_argument("--active", "-a", type=str, default=argparse.SUPPRESS, help="Active role(s) to highlight (comma-separated)")
    p_tasks.add_argument("--once", "-1", action="store_true", default=argparse.SUPPRESS, help="Print snapshot once and exit")
    p_tasks.add_argument("--interval", "-i", type=float, default=argparse.SUPPRESS, help="Refresh interval in seconds (default: 2.0)")
    p_tasks.add_argument("--watch", "-w", action="store_true", default=argparse.SUPPRESS, help="Force continuous watch loop")

    p_clean = subparsers.add_parser("clean", add_help=False, help="Remove all AI agent configurations in target repo")
    p_clean.add_argument("--lang", type=str, default=argparse.SUPPRESS, choices=["en", "vi"])
    p_clean.add_argument("--target", "-t", type=str, default=argparse.SUPPRESS, help="Target project/repo path")
    p_clean.add_argument("--yes", "-y", action="store_true", default=argparse.SUPPRESS, help="Confirm deletion without prompting")
    p_clean.add_argument("--dry-run", action="store_true", default=argparse.SUPPRESS, help="Preview files to be deleted without removing")

    p_fb = subparsers.add_parser("fallback", add_help=False, help="Configure or step down model fallback chains")
    p_fb.add_argument("--lang", type=str, default=argparse.SUPPRESS, choices=["en", "vi"])
    p_fb.add_argument("--target", "-t", type=str, default=argparse.SUPPRESS, help="Target project/repo path")
    p_fb.add_argument("--role", type=str, default="", help="Target role (or 'all') for --chain")
    p_fb.add_argument("--chain", type=str, default="", help="Custom fallback chain (comma or '->' separated)")
    p_fb.add_argument("--step-down", type=str, default="", help="Role (or 'all') to step down to next fallback model")

    p_menu = subparsers.add_parser("menu", add_help=False, help="Open interactive dashboard menu")
    p_menu.add_argument("--lang", type=str, default=argparse.SUPPRESS, choices=["en", "vi"])
    p_menu.add_argument("--target", "-t", type=str, default=argparse.SUPPRESS, help="Target project/repo path")

    return parser


def main() -> None:
    global CURRENT_LANG
    raw_argv = sys.argv[1:]
    lang = "en"
    if "--lang" in raw_argv:
        idx = raw_argv.index("--lang")
        if idx + 1 < len(raw_argv) and raw_argv[idx + 1] in ("vi", "en"):
            lang = raw_argv[idx + 1]
    CURRENT_LANG = lang

    if "-h" in raw_argv or "--help" in raw_argv:
        print_cli_help(lang=lang)
        return

    parser = build_cli_parser()
    args = parser.parse_args()
    CURRENT_LANG = lang if "--lang" in raw_argv else getattr(args, "lang", "en")
    projects_root = Path("/home/killua/Projects")

    if args.command == "list-skills":
        cmd_list_skills()
        return

    if args.command == "status":
        cmd_status(Path(args.target))
        return

    if args.command in ("ps", "tasks"):
        active_arg = getattr(args, "active", "")
        once_flag = getattr(args, "once", False)
        watch_flag = True if getattr(args, "watch", False) else (False if once_flag else None)
        interval = float(getattr(args, "interval", 2.0))
        cmd_ps(
            Path(args.target),
            active_arg=active_arg,
            watch=watch_flag,
            interval=interval,
        )
        return

    if args.command == "clean" or getattr(args, "clean", False):
        cmd_clean(
            Path(getattr(args, "target", ".")),
            auto_yes=getattr(args, "yes", False),
            dry_run=getattr(args, "dry_run", False),
        )
        return

    if args.command == "fallback":
        cmd_fallback(
            Path(args.target),
            role_arg=getattr(args, "role", ""),
            chain_arg=getattr(args, "chain", ""),
            step_down_arg=getattr(args, "step_down", ""),
        )
        return

    target_path = Path(getattr(args, "target", "."))
    auto_yes = getattr(args, "yes", False)
    dry_run = getattr(args, "dry_run", False)

    if args.command in (None, "menu") and not auto_yes and not dry_run and sys.stdin.isatty():
        run_interactive_dashboard(target_path, projects_root, lang=CURRENT_LANG)
        return

    if auto_yes:
        harnesses = [h.strip() for h in getattr(args, "harnesses", "agy,codex,claude").split(",") if h.strip()]
        bundles = [
            b.strip()
            for b in getattr(args, "bundles", "core-subagents-tdd,ponytail-lean,agy-swarm").split(",")
            if b.strip()
        ]
        cfg = build_preset_config(
            target_dir=target_path,
            goal=getattr(args, "goal", ""),
            context=getattr(args, "context", ""),
            harnesses=harnesses,
            bundles=bundles,
            skill_apply_mode=getattr(args, "skill_mode", "symlink"),
        )
    else:
        cfg = run_interactive_wizard(target_path, projects_root)

    created = write_project_configuration(cfg, dry_run=dry_run)
    print_summary(cfg, created, dry_run=dry_run)


if __name__ == "__main__":
    main()
