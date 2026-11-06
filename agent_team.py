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
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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


def c(text: str, color: str = "") -> str:
    if not sys.stdout.isatty():
        return text
    return f"{color}{text}{RESET}"


def banner() -> None:
    print(
        c(
            "\n╭──────────────────────────────────────────────────────────────────────────────╮\n"
            "│  🤖 AGT (AGENT-TEAM CLI) — Thiết lập Đội ngũ AI & Skills cho ~/Projects      │\n"
            "│  Chuẩn hóa: Antigravity (.agents) • OpenAI (.codex) • Claude Code (.claude)  │\n"
            "╰──────────────────────────────────────────────────────────────────────────────╯",
            BOLD + CYAN,
        )
    )


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


# ---------------------------------------------------------------------------
# Model & Role Catalogs (Đồng bộ chuẩn Orpheus / Act2Morse + Antigravity/Codex/Claude)
# ---------------------------------------------------------------------------
AGY_MODEL_CHOICES: List[Tuple[str, str]] = [
    ("gemini-4-argon-high", "Google Gemini 4 Argon (High) — Orchestrator / Kiến trúc phức tạp"),
    ("claude-opus-5-5-medium", "Anthropic Claude Opus 5.5 (Medium) — Orchestrator / Thiết kế sâu"),
    ("gemini-3.1-pro-high", "Google Gemini 3.1 Pro (High) — Reviewer / Kiểm định độc lập & Bảo mật"),
    ("gemini-3.8-flash-high", "Google Gemini 3.8 Flash (High) — Implementer / Viết code & TDD nhanh, chuẩn"),
    ("gemini-3.8-flash-medium", "Google Gemini 3.8 Flash (Medium) — Searcher / Trinh sát tài liệu & mã nguồn"),
    ("gemini-3.7-flash", "Google Gemini 3.7 Flash (Low) — Committer / Tác vụ gọn nhẹ"),
    ("inherit", "Kế thừa model hiện tại đang chọn trong phiên Antigravity"),
]

CODEX_MODEL_CHOICES: List[Tuple[str, str, str]] = [
    ("gpt-6-astra", "high", "OpenAI GPT-6 Astra (high) — Main Orchestrator & Integration"),
    ("gpt-6.1-sol", "xhigh", "OpenAI GPT-6.1 Sol (xhigh) — Deep Code Review, Security & Async Safety"),
    ("gpt-6-sol", "xhigh", "OpenAI GPT-6.0 Sol (xhigh) — Minimal Implementation & TDD Execution"),
    ("gpt-6-luna", "medium", "OpenAI GPT-6 Luna (medium) — Focused Searcher & Documentation Research"),
    ("gpt-6-luna-low", "low", "OpenAI GPT-6 Luna (low) — Concise Conventional Committer"),
    ("gpt-5-codex", "high", "OpenAI GPT-5 Codex (high) — Standard Coding Profile"),
    ("o3", "high", "OpenAI o3 (high) — Reasoning & Architecture"),
]

CLAUDE_MODEL_CHOICES: List[Tuple[str, str]] = [
    ("claude-opus-5-5-medium", "Claude Opus 5.5 Medium (Orchestrator / Deep Reasoning)"),
    ("opus", "Claude Opus (Lead Architect / Reviewer)"),
    ("sonnet", "Claude Sonnet (Implementer / Code Reviewer)"),
    ("haiku", "Claude Haiku (Fast Searcher / Committer)"),
    ("inherit", "Inherit từ phiên Claude Code hiện tại"),
]

READ_WRITE_TOOLS = [
    "run_command",
    "view_file",
    "write_to_file",
    "replace_file_content",
    "multi_replace_file_content",
    "grep_search",
    "find_by_name",
    "list_dir",
]

REVIEWER_TOOLS = [
    "view_file",
    "grep_search",
    "find_by_name",
    "list_dir",
    "run_command",
]

SEARCHER_TOOLS = [
    "view_file",
    "grep_search",
    "find_by_name",
    "search_web",
    "read_url_content",
]

COMMITTER_TOOLS = [
    "run_command",
    "view_file",
    "grep_search",
    "list_dir",
]

DEFAULT_AGENT_TEMPLATES: Dict[str, Dict] = {
    "orchestrator": {
        "title": "Astra / Argon: Architecture, Orchestration & Verification",
        "role": "Điều phối viên & Kiến trúc sư trưởng (Orchestrator)",
        "mission": (
            "Phân tích yêu cầu, chia nhỏ thành các task độc lập không chồng chéo file; "
            "giao việc cho implementer (code/test), reviewer (kiểm định độc lập), "
            "searcher (tra cứu tài liệu/codebase), và committer (tạo git commit). "
            "Kiểm tra hợp đồng giữa các module và đảm bảo toàn bộ ứng dụng build/test xanh."
        ),
        "provider": "multi",
        "agy_model": "gemini-4-argon-high",
        "claude_model": "claude-opus-5-5-medium",
        "codex_model": "gpt-6-astra",
        "reasoning_effort": "high",
        "context_scope": "Toàn bộ kiến trúc repo, AGENTS.md, module contracts và tích hợp hệ thống.",
        "goal_criteria": (
            "Không có 2 subagent sửa cùng 1 file; mọi phát hiện của reviewer được giải quyết triệt để; "
            "toàn bộ ứng dụng build và pass test trước khi báo cáo hoàn thành."
        ),
        "enable_write": True,
        "enable_subagents": True,
        "enable_mcp": True,
        "workspace_mode": "inherit",
        "agy_tools": list(READ_WRITE_TOOLS),
        "skills": [
            "brainstorming",
            "writing-plans",
            "subagent-driven-development",
            "dispatching-parallel-agents",
            "swarm",
        ],
    },
    "reviewer": {
        "title": "3.1 Pro High / Sol 6.1: Code Correctness, Security & Test Quality Review",
        "role": "Kiểm định viên chất lượng & Bảo mật (Reviewer)",
        "mission": (
            "Review code độc lập ở chế độ Read-Only: phát hiện lỗi logic, async race conditions, "
            "lỗ hổng bảo mật, dữ liệu đầu vào chưa kiểm tra, và chất lượng unit/regression test. "
            "Báo cáo chính xác file/dòng, nguyên nhân, mức độ ảnh hưởng và cách sửa nhỏ gọn nhất."
        ),
        "provider": "multi",
        "agy_model": "gemini-3.1-pro-high",
        "claude_model": "sonnet",
        "codex_model": "gpt-6.1-sol",
        "reasoning_effort": "xhigh",
        "context_scope": "Chế độ Read-Only trên git diff, các module liên đới và bộ kiểm thử.",
        "goal_criteria": (
            "Phân biệt rõ hành vi đã kiểm chứng với giả định; chỉ rõ file:line cho từng lỗi; "
            "không tự ý sửa đè lên file trừ khi được giao sửa một bug cụ thể."
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
    },
    "implementer": {
        "title": "3.8 Flash High / Sol 6.0: Minimal Implementation, TDD & Test Execution",
        "role": "Kỹ sư thực thi & Kiểm thử (Implementer)",
        "mission": (
            "Thực thi code và kiểm thử với thay đổi nhỏ gọn, trọn vẹn nhất (smallest complete changes): "
            "viết regression/unit test trước, chạy để xác nhận test fail (Red), sau đó viết code "
            "để pass (Green) và refactor sạch sẽ."
        ),
        "provider": "multi",
        "agy_model": "gemini-3.8-flash-high",
        "claude_model": "sonnet",
        "codex_model": "gpt-6-sol",
        "reasoning_effort": "xhigh",
        "context_scope": "Các module/file được phân công trong task brief và test suite tương ứng.",
        "goal_criteria": (
            "Tuân thủ kiến trúc và hợp đồng module hiện có; bảo toàn xử lý lỗi và dọn dẹp tài nguyên; "
            "báo cáo trung thực câu lệnh đã chạy và kết quả test thực tế."
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
    },
    "searcher": {
        "title": "Luna / 3.8 Flash Medium: Focused Research & Codebase Scout",
        "role": "Trinh sát mã nguồn & Tài liệu chính thống (Searcher)",
        "mission": (
            "Nghiên cứu các câu hỏi trọng tâm dựa trên tài liệu chính thống (primary documentation) "
            "và quét nhanh cấu trúc codebase ở chế độ Read-Only. Trả về kết quả cô đọng kèm URL, "
            "chữ ký hàm (API signatures), đường dẫn file:dòng và giới hạn tương thích."
        ),
        "provider": "multi",
        "agy_model": "gemini-3.8-flash-medium",
        "claude_model": "haiku",
        "codex_model": "gpt-6-luna",
        "reasoning_effort": "medium",
        "context_scope": "Read-Only trên toàn bộ codebase, tài liệu nội bộ và tìm kiếm web.",
        "goal_criteria": (
            "Xác minh thông tin trước khi đề xuất thư viện hoặc cấu hình; tuyệt đối không sửa code "
            "và không đưa thông tin nhạy cảm/secrets vào truy vấn tìm kiếm."
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
    },
    "committer": {
        "title": "3.7 Flash Low / Luna: Concise Conventional Git Commits",
        "role": "Chuyên viên Git Commit chuẩn Conventional Commits (Committer)",
        "mission": (
            "Kiểm tra trạng thái git (`git status -s`, `git diff --staged`) và tạo thông điệp commit "
            "ngắn gọn, chuyên nghiệp theo chuẩn Conventional Commits (`feat:`, `fix:`, `refactor:`, "
            "`test:`, `docs:`, `chore:`)."
        ),
        "provider": "multi",
        "agy_model": "gemini-3.7-flash",
        "claude_model": "haiku",
        "codex_model": "gpt-6-luna",
        "reasoning_effort": "low",
        "context_scope": "Git working tree, staged changes và lịch sử commit.",
        "goal_criteria": (
            "Subject line ở thể mệnh lệnh (imperative), chữ thường, tối đa 50-72 ký tự, không dấu chấm cuối; "
            "commit nguyên tử (atomic); tuyệt đối không commit secrets, API keys hay file cấu hình nhạy cảm."
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
    },
}

SKILL_BUNDLES: Dict[str, Dict[str, object]] = {
    "core-subagents-tdd": {
        "label": "Core Subagents, Planning & TDD (superpowers + mattpocock)",
        "description": "Quy trình điều phối subagents, lập kế hoạch, TDD, debug hệ thống và code review 2 trục.",
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
            "writing-for-agents",
        ],
    },
    "ponytail-lean": {
        "label": "Ponytail Lean / YAGNI Senior Mode (ponytail)",
        "description": "Giữ code tối giản, chống over-engineering, review thực dụng và kiểm toán nợ kỹ thuật.",
        "skills": [
            "ponytail",
            "ponytail-review",
            "ponytail-audit",
            "ponytail-debt",
            "ponytail-help",
        ],
    },
    "frontend-taste-ui": {
        "label": "Frontend Taste & UI/UX Pro Max (taste-skill + ui-ux-pro-max + Hephaestus UI)",
        "description": "Thiết kế giao diện chống AI-slop, minimalist/brutalist UI, animations, shadcn/tailwind.",
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
        "label": "Architecture Diagrams, Domain Modeling & Playwright (Hephaestus + mattpocock)",
        "description": "Vẽ kiến trúc hệ thống (archify), domain modeling, kiểm thử giao diện (playwright-cli).",
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
        "label": "Antigravity Native Swarm & Customizations (builtin)",
        "description": "Điều phối bầy đàn (Swarm message board) và tùy biến sâu hệ thống Antigravity.",
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
                    "description": description[:110] + ("..." if len(description) > 110 else ""),
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
        print("\nĐã hủy thiết lập.")
        sys.exit(0)
    return val if val else default


def ask_yes_no(prompt_label: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    try:
        val = input(f"{c('?', BOLD + GREEN)} {BOLD}{prompt_label}{RESET} [{c(hint, CYAN)}]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\nĐã hủy thiết lập.")
        sys.exit(0)
    if not val:
        return default
    return val in ("y", "yes", "co", "có", "1", "true")


def ask_choice(prompt_label: str, options: List[Tuple[str, str]], default_index: int = 0) -> str:
    print(f"\n{c('?', BOLD + GREEN)} {BOLD}{prompt_label}{RESET}")
    for idx, (key, desc) in enumerate(options, start=1):
        marker = c(" (mặc định)", YELLOW) if (idx - 1) == default_index else ""
        print(f"  {c(str(idx), BOLD + CYAN)}. {BOLD}{key}{RESET} — {desc}{marker}")
    raw = ask_text("Chọn số (hoặc nhập trực tiếp tên)", str(default_index + 1))
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
        "Nhập các số cách nhau bằng dấu phẩy (hoặc 'all' / Enter để giữ mặc định)",
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
    if resolved == projects_root.resolve():
        print(
            c(
                f"\n📂 Bạn đang ở thư mục gốc {projects_root}. Hãy chọn Project/Repo muốn thiết lập đội AI:",
                BOLD + YELLOW,
            )
        )
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
            badge = f"✓ Đã có: {', '.join(status_parts)}" if status_parts else "Chưa cài"
            stack = detect_tech_stack(d)
            options.append((d.name, f"{stack} ({badge})"))
        options.append(("[Tạo thư mục Project mới]", "Tạo một repo mới trong ~/Projects"))
        options.append(("[Thiết lập ngay tại ~/Projects]", "Tạo cấu hình cấp toàn cục cho ~/Projects"))

        choice = ask_choice("Chọn Project/Repo đích", options, default_index=0)
        if choice == "[Thiết lập ngay tại ~/Projects]":
            return projects_root
        if choice == "[Tạo thư mục Project mới]":
            new_name = ask_text("Nhập tên thư mục project mới (trong ~/Projects)", "my-new-project")
            target = (projects_root / new_name).expanduser().resolve()
            target.mkdir(parents=True, exist_ok=True)
            return target
        return (projects_root / choice).resolve()
    return resolved


def configure_single_agent(role_id: str, template: Dict, customize_deeply: bool) -> AgentSpec:
    print(
        c(
            f"\n─── Thiết lập Agent: [{role_id.upper()}] ({template['role']}) ───",
            BOLD + MAGENTA,
        )
    )
    if not customize_deeply:
        print(f"  • Nhiệm vụ     : {template['mission'][:95]}...")
        print(
            f"  • Model (Agy)  : {c(template['agy_model'], CYAN)} | Model (Codex): {c(template['codex_model'], CYAN)} ({template['reasoning_effort']}) | Claude: {c(template['claude_model'], CYAN)}"
        )
        print(f"  • Skills       : {', '.join(template['skills'])}")
        if not ask_yes_no(f"Bạn có muốn chỉnh sửa chi tiết cho agent '{role_id}' không?", default=False):
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
            )

    role_label = ask_text(f"[{role_id}] Tên vai trò (Role)", template["role"])
    title = ask_text(f"[{role_id}] Tiêu đề ngắn (Description header)", template["title"])
    mission = ask_text(f"[{role_id}] Nhiệm vụ cụ thể (Mission)", template["mission"])

    # Chọn Model cho Antigravity (agy)
    default_agy_idx = next(
        (i for i, (k, _) in enumerate(AGY_MODEL_CHOICES) if k == template["agy_model"]),
        0,
    )
    agy_opts = list(AGY_MODEL_CHOICES) + [("custom", "Tự nhập tên model bất kỳ cho Antigravity")]
    agy_model = ask_choice(f"[{role_id}] Chọn Model cho Antigravity (agy)", agy_opts, default_index=default_agy_idx)
    if agy_model == "custom":
        agy_model = ask_text(f"[{role_id}] Nhập tên model Antigravity", template["agy_model"])

    # Chọn Model cho OpenAI Codex (codex)
    codex_opts = [(k, f"{desc}") for k, _, desc in CODEX_MODEL_CHOICES] + [
        ("custom", "Tự nhập tên model bất kỳ cho OpenAI Codex")
    ]
    default_codex_idx = next(
        (i for i, (k, _, _) in enumerate(CODEX_MODEL_CHOICES) if k == template["codex_model"]),
        0,
    )
    codex_choice = ask_choice(f"[{role_id}] Chọn Model cho OpenAI Codex (.codex)", codex_opts, default_index=default_codex_idx)
    if codex_choice == "custom":
        codex_model = ask_text(f"[{role_id}] Nhập tên model Codex", template["codex_model"])
        reasoning_effort = ask_choice(
            f"[{role_id}] Mức độ suy luận (model_reasoning_effort)",
            [("xhigh", "Cực cao (xhigh)"), ("high", "Cao (high)"), ("medium", "Trung bình (medium)"), ("low", "Thấp/Nhanh (low)")],
            default_index=1,
        )
    else:
        matched = next((item for item in CODEX_MODEL_CHOICES if item[0] == codex_choice), None)
        if matched:
            codex_model = "gpt-6-luna" if matched[0] == "gpt-6-luna-low" else matched[0]
            reasoning_effort = matched[1]
        else:
            codex_model = codex_choice
            reasoning_effort = template["reasoning_effort"]

    # Chọn Model cho Claude Code (claude)
    default_claude_idx = next(
        (i for i, (k, _) in enumerate(CLAUDE_MODEL_CHOICES) if k == template["claude_model"]),
        0,
    )
    claude_opts = list(CLAUDE_MODEL_CHOICES) + [("custom", "Tự nhập tên model cho Claude Code")]
    claude_model = ask_choice(f"[{role_id}] Chọn Model cho Claude Code (.claude)", claude_opts, default_index=default_claude_idx)
    if claude_model == "custom":
        claude_model = ask_text(f"[{role_id}] Nhập tên model Claude", template["claude_model"])

    context_scope = ask_text(f"[{role_id}] Ngữ cảnh & Phạm vi (Context/Scope)", template["context_scope"])
    goal_criteria = ask_text(
        f"[{role_id}] Mục tiêu & Tiêu chí hoàn thành (Goal/Completion Criteria)",
        template["goal_criteria"],
    )

    enable_write = ask_yes_no(
        f"[{role_id}] Cấp quyền ghi/sửa file mã nguồn (Write tools)?",
        default=bool(template["enable_write"]),
    )
    enable_subagents = ask_yes_no(
        f"[{role_id}] Cho phép gọi subagents con?",
        default=bool(template["enable_subagents"]),
    )
    workspace_mode = "share" if enable_write and role_id != "orchestrator" else "inherit"
    agy_tools = list(READ_WRITE_TOOLS) if enable_write else list(template.get("agy_tools", REVIEWER_TOOLS))

    skills_raw = ask_text(
        f"[{role_id}] Skills gắn riêng cho agent này (cách nhau bằng dấu phẩy)",
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
    )


def run_interactive_wizard(target_dir: Path, projects_root: Path) -> TeamConfig:
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
                    f"\nℹ️ Phát hiện cấu hình đội AI đã có trong {project_name} (cập nhật: {existing_data.get('updated_at', '')}).",
                    YELLOW,
                )
            )
        except Exception:
            existing_data = None

    print(c(f"\n═══ BƯỚC 1: NGỮ CẢNH & MỤC TIÊU CỦA PROJECT [{project_name}] ═══", BOLD + BLUE))
    tech_stack = ask_text(
        "Tech Stack / Ngôn ngữ của Project",
        existing_data.get("tech_stack", detected_stack) if existing_data else detected_stack,
    )
    default_ctx = (
        existing_data.get("project_context")
        if existing_data
        else f"Dự án {project_name} ({tech_stack}). Giữ thay đổi nhỏ gọn (minimal complete changes), ưu tiên TDD và kiểm định độc lập."
    )
    project_context = ask_text("Ngữ cảnh chung của Project (kiến trúc, quy ước, lưu ý)", default_ctx)

    default_goal = (
        existing_data.get("project_goal")
        if existing_data
        else f"Phát triển, kiểm thử và duy trì {project_name} thông qua đội ngũ Multi-Agent điều phối trực tiếp."
    )
    project_goal = ask_text("Mục tiêu chính của Project hiện tại (Goal)", default_goal)

    # Quy tắc bổ sung (Graphify, Draw.io, Commit restriction...)
    rule_options = [
        (
            "graphify",
            "Graphify Rule (Ưu tiên `graphify query` trước khi đọc source nếu có `graphify-out/graph.json`, chạy `graphify update .` sau khi sửa code)",
        ),
        (
            "drawio-erd",
            "System Design / Draw.io Rule (Đọc `/home/killua/ryan/Study/System design/AGENTS.md` trước khi vẽ ERD/.drawio)",
        ),
        (
            "commit-restrictions",
            "Git Commit Restrictions Rule (Tạo `.agents/rules/commit-restrictions.md` chặn commit nhầm AGENTS.md / SKILL.md)",
        ),
    ]
    selected_extra_rules = ask_multi_choice(
        "Chọn các Quy tắc Đặc thù (Workspace Rules) muốn gắn vào Project này",
        rule_options,
        default_indices=[0, 1],
    )
    custom_rule = ask_text("Nhập thêm quy tắc đặc thù riêng của dự án (hoặc nhấn Enter để bỏ qua)", "")
    if custom_rule.strip():
        selected_extra_rules.append(f"custom:{custom_rule.strip()}")

    harness_options = [
        ("agy", "Google Antigravity (AGENTS.md, GEMINI.md, .agents/agents.json, .agents/agents/*/agent.md, .agents/skills.json)"),
        ("codex", "OpenAI Codex CLI (.codex/config.toml & .agents/agents/*/agent.toml)"),
        ("claude", "Anthropic Claude Code (CLAUDE.md & .claude/agents/*.md)"),
    ]
    harnesses = ask_multi_choice(
        "Chọn các công cụ điều phối cần sinh cấu hình",
        harness_options,
        default_indices=[0, 1, 2],
    )

    # Bước 2: Chọn đội hình Agents
    print(c("\n═══ BƯỚC 2: CHỌN ĐỘI HÌNH AGENTS & PHÂN CÔNG NHIỆM VỤ ═══", BOLD + BLUE))
    role_options = [
        ("orchestrator", "Điều phối viên & Kiến trúc sư (Agy: gemini-4-argon-high | Codex: gpt-6-astra high)"),
        ("reviewer", "Kiểm định viên độc lập Read-Only (Agy: gemini-3.1-pro-high | Codex: gpt-6.1-sol xhigh)"),
        ("implementer", "Kỹ sư thực thi & TDD (Agy: gemini-3.8-flash-high | Codex: gpt-6-sol xhigh)"),
        ("searcher", "Trinh sát tài liệu & Codebase (Agy: gemini-3.8-flash-medium | Codex: gpt-6-luna medium)"),
        ("committer", "Chuyên viên Git Commit chuẩn (Agy: gemini-3.7-flash | Codex: gpt-6-luna low)"),
    ]
    selected_roles = ask_multi_choice(
        "Chọn các Agents trong đội hình của Project này",
        role_options,
        default_indices=[0, 1, 2, 3, 4],
    )

    while ask_yes_no("Bạn có muốn thêm một Agent chuyên biệt mới (VD: ui-designer, security-auditor, ml-tuner)?", default=False):
        custom_id = ask_text("Nhập ID cho agent mới (viết thường, nối bằng dấu gạch ngang)", "custom-specialist")
        custom_id = re.sub(r"[^a-z0-9_-]", "-", custom_id.lower()).strip("-") or "custom-agent"
        if custom_id not in DEFAULT_AGENT_TEMPLATES:
            DEFAULT_AGENT_TEMPLATES[custom_id] = {
                "title": f"Specialized {custom_id.replace('-', ' ').title()} Agent",
                "role": f"Chuyên gia {custom_id}",
                "mission": f"Thực hiện các tác vụ chuyên sâu về {custom_id} theo sự điều phối của Orchestrator.",
                "provider": "multi",
                "agy_model": "gemini-3.8-flash-high",
                "claude_model": "sonnet",
                "codex_model": "gpt-6-sol",
                "reasoning_effort": "high",
                "context_scope": f"Các module và tài liệu liên quan đến {custom_id}.",
                "goal_criteria": f"Hoàn thành trọn vẹn tác vụ {custom_id} với kết quả kiểm chứng được.",
                "enable_write": True,
                "enable_subagents": False,
                "enable_mcp": True,
                "workspace_mode": "share",
                "agy_tools": list(READ_WRITE_TOOLS),
                "skills": [],
            }
        if custom_id not in selected_roles:
            selected_roles.append(custom_id)

    setup_mode_options = [
        ("guided", "Đi qua từng Agent để đặt câu hỏi chi tiết (Nhiệm vụ, Model, Provider, Ngữ cảnh, Mục tiêu)"),
        ("quick", "Xem tóm tắt chuẩn Orpheus/Act2Morse cho từng Agent và chỉ chỉnh sửa Agent nào cần đổi"),
    ]
    setup_mode = ask_choice("Chọn chế độ thiết lập từng Agent", setup_mode_options, default_index=0)
    customize_deeply = setup_mode == "guided"

    agents: List[AgentSpec] = []
    for role_id in selected_roles:
        tpl = dict(DEFAULT_AGENT_TEMPLATES[role_id])
        if existing_data and "agents" in existing_data:
            for old_ag in existing_data["agents"]:
                if old_ag.get("id") == role_id:
                    tpl.update(old_ag)
        spec = configure_single_agent(role_id, tpl, customize_deeply)
        agents.append(spec)

    # Bước 3: Chọn & Apply Skills
    print(c("\n═══ BƯỚC 3: CHỌN & APPLY SKILLS VÀO PROJECT / REPO ═══", BOLD + BLUE))
    discovered_skills = discover_local_skills()
    print(
        f"Đã quét thấy {c(str(len(discovered_skills)), BOLD + GREEN)} skills từ `~/.gemini/config/plugins`, "
        f"`Hephaestus/.agents/skills`, và `builtin`."
    )
    bundle_keys = list(SKILL_BUNDLES.keys())
    bundle_opts = [(k, f"{SKILL_BUNDLES[k]['label']} — {SKILL_BUNDLES[k]['description']}") for k in bundle_keys]
    chosen_bundles = ask_multi_choice(
        "Chọn các Gói Kỹ năng (Skill Bundles) muốn apply cho Project này",
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
        "Nhập thêm tên các skills lẻ muốn gắn thêm (VD: archify, minimalist-ui, playwright-cli... hoặc Enter)",
        "",
    )
    if extra_skills_raw.strip():
        for s in extra_skills_raw.split(","):
            if s.strip():
                skill_names_set.add(s.strip())

    apply_mode_opts = [
        (
            "symlink",
            "Khai báo `.agents/skills.json` + Tạo symlink trực tiếp vào `.agents/skills/` (Nhẹ, tự động cập nhật, mọi công cụ đều đọc được)",
        ),
        (
            "copy",
            "Khai báo `.agents/skills.json` + Copy toàn bộ thư mục skill vào `.agents/skills/` (Giống Hephaestus, độc lập hoàn toàn)",
        ),
        (
            "json-only",
            "Chỉ khai báo đường dẫn trong `.agents/skills.json` (Giữ thư mục `.agents/skills/` gọn nhất)",
        ),
    ]
    skill_apply_mode = ask_choice("Cách thức Apply Skills vào Project", apply_mode_opts, default_index=0)

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


def build_root_agents_md(cfg: TeamConfig, existing_content: Optional[str] = None) -> str:
    """
    Sinh hoặc cập nhật AGENTS.md tại gốc repo theo đúng chuẩn Orpheus / Act2Morse (< 150 lines):
    - Nếu repo đã có sẵn AGENTS.md với các mục riêng (như Project Structure, Build Commands...),
      giữ nguyên phần hướng dẫn riêng của repo và cập nhật mục `## Agent-Specific Instructions`!
    """
    subagent_lines = [
        "- Workspace subagents are located in `.agents/agents/{agent_name}/agent.md` (and configured for Codex in `.agents/agents/{agent_name}/agent.toml` via `.codex/config.toml`):"
    ]
    for ag in cfg.agents:
        subagent_lines.append(
            f"  - `{ag.id}`: `.agents/agents/{ag.id}/agent.md` "
            f"(Agy: `{ag.agy_model}`, Codex: `{ag.codex_model}` {ag.reasoning_effort}) — {ag.role}"
        )

    extra_bullets = format_extra_rules_bullets(cfg)
    skills_summary = ", ".join(f"`{s['name']}`" for s in cfg.selected_skills[:12])
    if len(cfg.selected_skills) > 12:
        skills_summary += f" (+{len(cfg.selected_skills) - 12} more in `.agents/skills.json`)"

    agent_section_lines = [
        "## Agent-Specific Instructions",
        "",
        f"- **Project Context**: {cfg.project_context}",
        f"- **Primary Goal**: {cfg.project_goal}",
        "- **Line Limit**: Keep `AGENTS.md` strictly under 150 lines; put detailed specs in `.agents/README.md`.",
        *extra_bullets,
        *subagent_lines,
        f"- **Applied Workspace Skills**: {skills_summary or 'See `.agents/skills.json`'}.",
        "- Read `.agents/README.md` for the full role & model mapping table.",
    ]
    agent_section = "\n".join(agent_section_lines)

    if existing_content and "## Agent-Specific Instructions" in existing_content:
        prefix_lines = existing_content.split("## Agent-Specific Instructions")[0].rstrip().splitlines()
        max_prefix = MAX_AGENTS_MD_LINES - len(agent_section_lines) - 2
        if len(prefix_lines) > max_prefix:
            prefix_lines = prefix_lines[:max_prefix]
        combined = "\n".join(prefix_lines) + "\n\n" + agent_section
        return enforce_agents_md_line_limit(combined)

    fresh = "\n".join(
        [
            f"# Repository & Agent Guidelines — {cfg.project_name}",
            "",
            "## Project Context & Goals",
            "",
            f"- **Tech Stack**: {cfg.tech_stack}",
            f"- **Context**: {cfg.project_context}",
            f"- **Current Goal**: {cfg.project_goal}",
            "",
            "## Team Topology & Delegation Rules",
            "",
            "- Avoid overlapping file ownership between subagents.",
            "- Assign bounded implementation and testing tasks to `implementer`.",
            "- Assign independent, read-only code review to `reviewer` before claiming completion.",
            "- Assign focused documentation and codebase exploration to `searcher`.",
            "- Assign concise Conventional Commits creation to `committer`.",
            "",
            agent_section,
        ]
    )
    return enforce_agents_md_line_limit(fresh)


def build_agents_readme_md(cfg: TeamConfig) -> str:
    """Sinh file .agents/README.md theo đúng chuẩn Orpheus / Act2Morse."""
    rows = []
    for ag in cfg.agents:
        rows.append(
            f"| `{ag.id}` | `.agents/agents/{ag.id}/agent.md` | `{ag.agy_model}` | `{ag.codex_model}` ({ag.reasoning_effort}) | {ag.role} — {ag.mission} |"
        )
    rows_block = "\n".join(rows)

    skill_rows = []
    for s in cfg.selected_skills:
        skill_rows.append(f"- **`{s['name']}`** ({s['plugin']}): {s['description']}")
    skills_block = "\n".join(skill_rows) if skill_rows else "- Chưa gắn skill bổ sung."

    return (
        f"# {cfg.project_name} Agents & Skills\n\n"
        f"Workspace subagents are located in `.agents/agents/{{agent_name}}/agent.md`.\n\n"
        f"Both **Codex**, **Claude Code**, and **Antigravity CLI (`agy`)** discover the agents in this workspace:\n"
        f"- **agy** reads `.agents/agents/{{agent_name}}/agent.md`, `.agents/agents.json`, and `.agents/skills.json`.\n"
        f"- **Codex** reads `.agents/agents/{{agent_name}}/agent.toml` registered via `../.codex/config.toml`.\n"
        f"- **Claude Code** reads `.claude/agents/{{agent_name}}.md` and `CLAUDE.md`.\n\n"
        f"## Agent Roles & Model Mapping\n\n"
        f"| Role | Workspace Path | Model (Agy) | Model (Codex) | Purpose |\n"
        f"| --- | --- | --- | --- | --- |\n"
        f"{rows_block}\n\n"
        f"## Project Context & Goal\n\n"
        f"- **Context**: {cfg.project_context}\n"
        f"- **Goal**: {cfg.project_goal}\n\n"
        f"## Applied Skills ({len(cfg.selected_skills)})\n\n"
        f"{skills_block}\n"
    )


def build_agents_json(cfg: TeamConfig) -> List[Dict[str, str]]:
    """Sinh file .agents/agents.json theo đúng chuẩn Orpheus / Act2Morse."""
    return [
        {
            "name": ag.id,
            "path": f"agents/{ag.id}/agent.md",
        }
        for ag in cfg.agents
    ]


def build_single_agent_md(cfg: TeamConfig, ag: AgentSpec) -> str:
    """
    Sinh file `.agents/agents/<role>/agent.md` theo đúng chuẩn YAML frontmatter của Antigravity:
    name, description, model, tools + Markdown instructions.
    """
    tools_yaml = "\n".join(f"  - {t}" for t in ag.agy_tools)
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

    return (
        f"---\n"
        f"name: {ag.id}\n"
        f"description: \"{ag.title}\"\n"
        f"model: {ag.agy_model}\n"
        f"tools:\n"
        f"{tools_yaml}\n"
        f"---\n\n"
        f"# {ag.id.replace('-', ' ').title()} Instructions\n\n"
        f"Project: **{cfg.project_name}** ({cfg.tech_stack})\n"
        f"- **Role**: {ag.role}\n"
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

    instructions = (
        f"Role: {ag.role} for {cfg.project_name}.\n"
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
        f"Act as {cfg.project_name}'s orchestrator. Delegate implementation and tests to implementer,",
        "code review to reviewer, concise commits to committer, and focused documentation/code searches to searcher.",
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
    tools_str = "Read, Edit, Write, Bash, Grep, Glob" if ag.enable_write else "Read, Grep, Glob, Bash"
    model_line = f"model: {ag.claude_model}\n" if ag.claude_model != "inherit" else ""
    skills_str = ", ".join(ag.skills) if ag.skills else "Theo ngữ cảnh"
    return (
        f"---\n"
        f"name: {ag.id}\n"
        f"description: \"{ag.title} — {ag.role}\"\n"
        f"tools: {tools_str}\n"
        f"{model_line}"
        f"---\n\n"
        f"# {ag.id.replace('-', ' ').title()} ({cfg.project_name})\n\n"
        f"- **Mission**: {ag.mission}\n"
        f"- **Context & Scope**: {ag.context_scope}\n"
        f"- **Goal & Completion Criteria**: {ag.goal_criteria}\n"
        f"- **Preferred Skills**: {skills_str}\n"
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

    # 1. Root AGENTS.md
    save("AGENTS.md", build_root_agents_md(cfg, existing_agents_md))

    # 2. Chuẩn .agents/ (Dùng chung cho cả Antigravity `agy` và OpenAI `codex`)
    save(".agents/README.md", build_agents_readme_md(cfg))
    save(".agents/agents.json", json.dumps(build_agents_json(cfg), indent=2, ensure_ascii=False) + "\n")
    save(".agents/skills.json", json.dumps(build_agy_skills_json(cfg), indent=2, ensure_ascii=False) + "\n")

    for ag in cfg.agents:
        save(f".agents/agents/{ag.id}/agent.md", build_single_agent_md(cfg, ag))
        save(f".agents/agents/{ag.id}/agent.toml", build_single_agent_toml(cfg, ag))

    if cfg.add_commit_restrictions:
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
        created_files.append(str(project_path / f".agents/skills/ ({len(skill_paths)} skills {cfg.skill_apply_mode})"))

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

    agents: List[AgentSpec] = []
    for role_id in ("orchestrator", "reviewer", "implementer", "committer", "searcher"):
        tpl = DEFAULT_AGENT_TEMPLATES[role_id]
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

    return TeamConfig(
        project_name=project_name,
        project_path=str(project_path),
        tech_stack=tech_stack,
        project_context=context
        or f"Dự án {project_name} ({tech_stack}). Giữ thay đổi nhỏ gọn, ưu tiên TDD và kiểm định độc lập.",
        project_goal=goal
        or f"Phát triển, kiểm thử và duy trì {project_name} thông qua đội ngũ 5 Agents chuẩn (Orchestrator, Reviewer, Implementer, Committer, Searcher).",
        extra_rules=["graphify", "drawio-erd"],
        harnesses=harnesses,
        skill_apply_mode=skill_apply_mode,
        add_commit_restrictions=False,
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

    print(f"\nTìm thấy tổng cộng {c(str(len(discovered)), BOLD + GREEN)} skills trên máy:\n")
    for plugin, items in sorted(by_plugin.items()):
        print(c(f"📦 Nguồn/Plugin: {plugin} ({len(items)} skills)", BOLD + CYAN))
        for item in sorted(items, key=lambda x: x["name"]):
            print(f"   • {BOLD}{item['name']}{RESET}: {item['description']}")
        print()


def cmd_status(target_dir: Path) -> None:
    project_path = target_dir.resolve()
    cfg_file = project_path / ".agents" / "team-config.json"
    agents_json = project_path / ".agents" / "agents.json"

    if cfg_file.exists():
        data = json.loads(cfg_file.read_text(encoding="utf-8"))
        print(c(f"\n📊 Trạng thái Đội ngũ AI tại: {data['project_name']} ({data['project_path']})", BOLD + GREEN))
        print(f"  • Tech Stack : {data.get('tech_stack')}")
        print(f"  • Mục tiêu   : {data.get('project_goal')}")
        print(f"  • Công cụ    : {', '.join(data.get('harnesses', []))}")
        print(f"  • Skill Mode : {data.get('skill_apply_mode')}")
        print(f"  • Cập nhật   : {data.get('updated_at')}")
        print(c("\n  🤖 Danh sách Agents:", BOLD + CYAN))
        for ag in data.get("agents", []):
            w = "Write" if ag.get("enable_write") else "Read-Only"
            print(
                f"     - [{BOLD}{ag['id']}{RESET}] {ag['role']}\n"
                f"       Agy: {c(ag['agy_model'], CYAN)} | Codex: {c(ag['codex_model'], CYAN)} ({ag.get('reasoning_effort', 'high')}) | Claude: {c(ag['claude_model'], CYAN)} [{w}]"
            )
        skills = [s["name"] for s in data.get("selected_skills", [])]
        print(c(f"\n  🧩 Skills đã gắn ({len(skills)}):", BOLD + CYAN))
        print("     " + ", ".join(skills))
        return

    if agents_json.exists():
        items = json.loads(agents_json.read_text(encoding="utf-8"))
        print(c(f"\n📊 Phát hiện cấu hình `.agents/agents.json` tại {project_path.name}:", BOLD + GREEN))
        for item in items:
            print(f"   • {BOLD}{item.get('name')}{RESET} -> `.agents/{item.get('path')}`")
        return

    print(c(f"⚠️ Chưa tìm thấy cấu hình đội AI tại {project_path}", YELLOW))
    print("Hãy gõ `agt` để khởi tạo ngay.")


def print_summary(cfg: TeamConfig, created_files: List[str], dry_run: bool = False) -> None:
    prefix = "[DRY-RUN] Dự kiến tạo" if dry_run else "✅ Đã khởi tạo thành công"
    print(c(f"\n{prefix} bộ cấu hình Đội ngũ AI & Skills cho [{cfg.project_name}]!", BOLD + GREEN))
    print(f"📍 Thư mục đích: {BOLD}{cfg.project_path}{RESET}\n")
    print(c("📄 Các file cấu hình đã sinh ra:", BOLD + CYAN))
    for f in created_files:
        rel = os.path.relpath(f, cfg.project_path) if f.startswith(cfg.project_path) else f
        print(f"   • {rel}")

    print(c("\n🚀 Cách sử dụng ngay trong công cụ bạn đang mở:", BOLD + YELLOW))
    print(
        f"  • {BOLD}Antigravity (`agy`){RESET}   : Tự động nhận diện `.agents/agents.json`, `.agents/agents/*/agent.md`, và `.agents/skills.json`.\n"
        f"  • {BOLD}OpenAI Codex (`codex`){RESET}: Tự động nhận diện `[agents]` trong `.codex/config.toml` trỏ tới `.agents/agents/*/agent.toml`.\n"
        f"  • {BOLD}Claude Code (`claude`){RESET}: Tự động nhận diện `CLAUDE.md` và `.claude/agents/*.md`.\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agt",
        description="CLI Wizard (agt) thiết lập đội ngũ Multi-Agent (Orchestrator, Reviewer, Implementer, Committer, Searcher) & Skills cho ~/Projects.",
    )
    subparsers = parser.add_subparsers(dest="command")

    p_init = subparsers.add_parser("init", help="Chạy wizard thiết lập đội ngũ AI cho một Project/Repo")
    p_init.add_argument("--target", "-t", type=str, default=".", help="Đường dẫn tới project/repo cần thiết lập")
    p_init.add_argument("--yes", "-y", action="store_true", help="Chạy tự động với preset chuẩn Orpheus/Act2Morse")
    p_init.add_argument("--goal", type=str, default="", help="Mục tiêu chính của project (dùng kèm --yes)")
    p_init.add_argument("--context", type=str, default="", help="Ngữ cảnh của project (dùng kèm --yes)")
    p_init.add_argument(
        "--harnesses",
        type=str,
        default="agy,codex,claude",
        help="Danh sách công cụ cần xuất cấu hình: agy,codex,claude",
    )
    p_init.add_argument(
        "--bundles",
        type=str,
        default="core-subagents-tdd,ponytail-lean,agy-swarm",
        help="Các gói skill cần gắn (cách nhau dấu phẩy)",
    )
    p_init.add_argument(
        "--skill-mode",
        type=str,
        default="symlink",
        choices=["symlink", "copy", "json-only"],
        help="Chế độ apply skills vào .agents/skills/ (symlink, copy, json-only)",
    )
    p_init.add_argument("--dry-run", action="store_true", help="Chỉ hiển thị danh sách file sẽ tạo, không ghi xuống đĩa")

    subparsers.add_parser("list-skills", help="Liệt kê toàn bộ Skills đang có trên máy (Plugins + Hephaestus + Builtin)")

    p_status = subparsers.add_parser("status", help="Xem cấu hình đội ngũ AI hiện tại của một Project")
    p_status.add_argument("--target", "-t", type=str, default=".", help="Đường dẫn tới project/repo")

    args = parser.parse_args()
    projects_root = Path("/home/killua/Projects")

    if args.command == "list-skills":
        cmd_list_skills()
        return

    if args.command == "status":
        cmd_status(Path(args.target))
        return

    target_path = Path(getattr(args, "target", "."))
    auto_yes = getattr(args, "yes", False)
    dry_run = getattr(args, "dry_run", False)

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
