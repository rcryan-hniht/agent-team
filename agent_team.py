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


CURRENT_LANG = "en"


def tr(en_text: str, vi_text: str) -> str:
    return vi_text if CURRENT_LANG == "vi" else en_text


def c(text: str, color: str = "") -> str:
    if not sys.stdout.isatty():
        return text
    return f"{color}{text}{RESET}"


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _visible_len(text: str) -> int:
    return len(ANSI_ESCAPE_RE.sub("", text))


def _box_line(text: str, inner_width: int = 54) -> str:
    pad = max(0, inner_width - _visible_len(text))
    return f"{c('│', CYAN)}  {text}{' ' * pad}  {c('│', CYAN)}"


def banner() -> None:
    box_w = 52
    ascii_art = [
        c("   █████╗  ██████╗ ████████╗", BOLD + CYAN),
        c("  ██╔══██╗██╔════╝ ╚══██╔══╝", BOLD + CYAN),
        c("  ███████║██║  ███╗   ██║   ", BOLD + CYAN),
        c("  ██╔══██║██║   ██║   ██║   ", BOLD + GREEN),
        c("  ██║  ██║╚██████╔╝   ██║   ", BOLD + GREEN),
        c("  ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ", DIM + GREEN),
    ]

    if CURRENT_LANG == "vi":
        header_title = " ✦ AGENT-TEAM // ĐIỀU PHỐI ĐỘI NGŨ AI & SKILLS "
        line_1 = f"{c('▸ HARNESS', BOLD + YELLOW)} : Antigravity • OpenAI Codex • Claude Code"
        line_2 = f"{c('▸ AGENTS ', BOLD + GREEN)} : Orchestrator • Reviewer • Implementer"
        line_3 = f"            Searcher • Committer • Custom Roles"
        footer_tag = " ◈ .agents   ◈ .codex   ◈ .claude   ◈ 150+ skills "
    else:
        header_title = " ✦ AGENT-TEAM // MULTI-AGENT & SKILLS GENERATOR "
        line_1 = f"{c('▸ HARNESS', BOLD + YELLOW)} : Antigravity • OpenAI Codex • Claude Code"
        line_2 = f"{c('▸ ROSTER ', BOLD + GREEN)} : Orchestrator • Reviewer • Implementer"
        line_3 = f"            Searcher • Committer • Custom Roles"
        footer_tag = " ◈ .agents   ◈ .codex   ◈ .claude   ◈ 150+ skills "

    top_dashes = max(1, (box_w + 4) - len(header_title) - 3)
    bot_dashes = max(1, (box_w + 4) - len(footer_tag) - 3)

    right_rows = [
        f"{c('╭───', CYAN)}{c(header_title, BOLD + CYAN)}{c('─' * top_dashes + '╮', CYAN)}",
        _box_line(line_1, box_w),
        _box_line(line_2, box_w),
        _box_line(line_3, box_w),
        f"{c('╰───', CYAN)}{c(footer_tag, DIM + CYAN)}{c('─' * bot_dashes + '╯', CYAN)}",
        f"   {c('⚡', YELLOW)} {c('cd ~/project-example && agt', DIM)}",
    ]

    print()
    for left, right in zip(ascii_art, right_rows):
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

DEFAULT_AGENT_TEMPLATES_EN: Dict[str, Dict] = {
    "orchestrator": {
        "title": "Astra / Argon: Architecture, Orchestration & Verification",
        "role": "Lead Orchestrator & Architect",
        "mission": (
            "Break down requirements into bounded, non-overlapping tasks; delegate implementation "
            "and testing to implementer, independent review to reviewer, documentation/code research "
            "to searcher, and git commits to committer. Verify module contracts and final build/tests."
        ),
        "provider": "multi",
        "agy_model": "gemini-4-argon-high",
        "claude_model": "claude-opus-5-5-medium",
        "codex_model": "gpt-6-astra",
        "reasoning_effort": "high",
        "context_scope": "Full repository architecture, AGENTS.md, module contracts, and system integration.",
        "goal_criteria": (
            "Zero overlapping file ownership across subagents; all reviewer findings resolved; "
            "full application builds and passes tests before claiming completion."
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
    },
}

DEFAULT_AGENT_TEMPLATES_VI: Dict[str, Dict] = {
    "orchestrator": {
        "title": "Astra / Argon: Kiến trúc, Điều phối & Kiểm chứng tích hợp",
        "role": "Điều phối viên & Kiến trúc sư trưởng",
        "mission": (
            "Phân rã yêu cầu thành các tác vụ độc lập, không chồng chéo quyền sửa file; giao thực thi code & test "
            "cho implementer, kiểm định độc lập cho reviewer, tra cứu tài liệu/codebase cho searcher, và đóng gói "
            "git commit cho committer. Kiểm chứng hợp đồng giữa các module và kết quả build/test cuối cùng."
        ),
        "provider": "multi",
        "agy_model": "gemini-4-argon-high",
        "claude_model": "claude-opus-5-5-medium",
        "codex_model": "gpt-6-astra",
        "reasoning_effort": "high",
        "context_scope": "Toàn bộ kiến trúc repo, AGENTS.md, hợp đồng module và tích hợp hệ thống.",
        "goal_criteria": (
            "Không có 2 subagent sửa cùng một file; mọi phát hiện của reviewer được xử lý triệt để; "
            "ứng dụng build và vượt qua toàn bộ bài test trước khi báo cáo hoàn thành."
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
    if not customize_deeply:
        print(f"  • {tr('Mission     ', 'Nhiệm vụ     ')}: {template['mission'][:95]}...")
        print(
            f"  • Model (Agy)  : {c(template['agy_model'], CYAN)} | Model (Codex): {c(template['codex_model'], CYAN)} ({template['reasoning_effort']}) | Claude: {c(template['claude_model'], CYAN)}"
        )
        print(f"  • Skills       : {', '.join(template['skills'])}")
        if not ask_yes_no(
            tr(f"Customize details for agent '{role_id}'?", f"Bạn có muốn chỉnh sửa chi tiết cho agent '{role_id}' không?"),
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
            "orchestrator",
            tr(
                "Lead Orchestrator & Architect — Agy: gemini-4-argon-high | Codex: gpt-6-astra high",
                "Điều phối viên & Kiến trúc sư trưởng — Agy: gemini-4-argon-high | Codex: gpt-6-astra high",
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
        default_indices=[0, 1, 2, 3, 4],
    )

    active_templates = get_agent_templates()
    while ask_yes_no(
        tr(
            "Add a custom specialist Agent (e.g. ui-designer, security-auditor, ml-tuner)?",
            "Bạn có muốn thêm một Agent chuyên biệt mới (VD: ui-designer, security-auditor, ml-tuner)?",
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
            }
        if custom_id not in selected_roles:
            selected_roles.append(custom_id)

    setup_mode_options = [
        (
            "guided",
            tr(
                "Step through each Agent with detailed prompts (Mission, Model, Provider, Context, Goal)",
                "Đi qua từng Agent để đặt câu hỏi chi tiết (Nhiệm vụ, Model, Provider, Ngữ cảnh, Mục tiêu)",
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
                    for k in ("agy_model", "claude_model", "codex_model", "reasoning_effort", "enable_write", "enable_subagents", "enable_mcp", "workspace_mode", "agy_tools", "skills"):
                        if k in old_ag:
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
    skills_summary = ", ".join(f"`{s['name']}`" for s in cfg.selected_skills)

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
        skill_rows.append(f"- **`{s['name']}`**: {s['description']}")
    skills_block = "\n".join(skill_rows) if skill_rows else "- None"

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
        f"## Applied Skills\n\n"
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
    for role_id in ("orchestrator", "reviewer", "implementer", "committer", "searcher"):
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
        or tr(
            f"{project_name} ({tech_stack}). Keep changes small and complete, prioritize TDD and independent code review.",
            f"Dự án {project_name} ({tech_stack}). Giữ thay đổi nhỏ gọn, ưu tiên TDD và kiểm định độc lập.",
        ),
        project_goal=goal
        or tr(
            f"Develop, test, and maintain {project_name} through a 5-Agent team (Orchestrator, Reviewer, Implementer, Committer, Searcher).",
            f"Phát triển, kiểm thử và duy trì {project_name} thông qua đội ngũ 5 Agents chuẩn (Orchestrator, Reviewer, Implementer, Committer, Searcher).",
        ),
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
    project_path = target_dir.resolve()
    cfg_file = project_path / ".agents" / "team-config.json"
    agents_json = project_path / ".agents" / "agents.json"

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
        active_templates = get_agent_templates()
        print(
            c(
                tr(
                    f"\n📊 AI Team Status at: {proj_name} ({data['project_path']})",
                    f"\n📊 Trạng thái Đội ngũ AI tại: {proj_name} ({data['project_path']})",
                ),
                BOLD + GREEN,
            )
        )
        print(f"  • Tech Stack : {data.get('tech_stack')}")
        print(f"  • {tr('Goal       ', 'Mục tiêu   ')}: {display_goal}")
        print(f"  • {tr('Harnesses  ', 'Công cụ    ')}: {', '.join(data.get('harnesses', []))}")
        print(f"  • Skill Mode : {data.get('skill_apply_mode')}")
        print(f"  • {tr('Updated    ', 'Cập nhật   ')}: {data.get('updated_at')}")
        print(c(tr("\n  🤖 Agent Roster:", "\n  🤖 Danh sách Agents:"), BOLD + CYAN))
        for ag in data.get("agents", []):
            role_id = ag.get("id", "")
            stored_role = str(ag.get("role", ""))
            if not _matches_current_lang(stored_role):
                if role_id in active_templates:
                    display_role = active_templates[role_id]["role"]
                else:
                    display_role = tr(f"Specialist — {role_id}", f"Chuyên gia — {role_id}")
            else:
                display_role = stored_role
            w = tr("Write", "Ghi/Sửa") if ag.get("enable_write") else tr("Read-Only", "Chỉ đọc")
            print(
                f"     - [{BOLD}{role_id}{RESET}] {display_role}\n"
                f"       Agy: {c(ag['agy_model'], CYAN)} | Codex: {c(ag['codex_model'], CYAN)} ({ag.get('reasoning_effort', 'high')}) | Claude: {c(ag['claude_model'], CYAN)} [{w}]"
            )
        skills = [s["name"] for s in data.get("selected_skills", [])]
        print(c(tr("\n  🧩 Applied Skills:", "\n  🧩 Skills đã gắn:"), BOLD + CYAN))
        print("     " + ", ".join(skills))
        return

    if agents_json.exists():
        items = json.loads(agents_json.read_text(encoding="utf-8"))
        print(
            c(
                tr(
                    f"\n📊 Detected `.agents/agents.json` in {project_path.name}:",
                    f"\n📊 Phát hiện cấu hình `.agents/agents.json` tại {project_path.name}:",
                ),
                BOLD + GREEN,
            )
        )
        for item in items:
            print(f"   • {BOLD}{item.get('name')}{RESET} -> `.agents/{item.get('path')}`")
        return

    print(
        c(
            tr(
                f"⚠️ No AI Team configuration found at {project_path}",
                f"⚠️ Chưa tìm thấy cấu hình đội AI tại {project_path}",
            ),
            YELLOW,
        )
    )
    print(tr("Run `agt` to initialize now.", "Hãy gõ `agt` để khởi tạo ngay."))


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
            f"  {c('status', BOLD + CYAN)}        Inspect active Agent roster, models, and skills in a Project\n"
            f"  {c('list-skills', BOLD + CYAN)}   List all discovered local Skills\n\n"
            f"{c('OPTIONS:', BOLD + YELLOW)}\n"
            f"  {c('-t, --target <path>', CYAN)}     Target project directory (default: current directory)\n"
            f"  {c('-y, --yes', CYAN)}               Non-interactive mode using standard 5-agent preset\n"
            f"  {c('--goal <text>', CYAN)}           Primary project goal (used with --yes)\n"
            f"  {c('--context <text>', CYAN)}        Project context description (used with --yes)\n"
            f"  {c('--harnesses <list>', CYAN)}      Target harnesses: agy,codex,claude (default: all)\n"
            f"  {c('--skill-mode <mode>', CYAN)}     Skill linking mode: symlink | copy | json-only\n"
            f"  {c('--lang <en|vi>', CYAN)}          CLI display language: en (English, default) or vi (Tiếng Việt)\n"
            f"  {c('--dry-run', CYAN)}               Preview generated files without writing to disk\n"
            f"  {c('-h, --help', CYAN)}              Show this help message\n\n"
            f"{c('EXAMPLES:', BOLD + YELLOW)}\n"
            f"  • Launch interactive setup in a project      : {c('cd ~/project-example && agt', GREEN)}\n"
            f"  • Launch in Vietnamese mode                  : {c('agt --lang vi', GREEN)}\n"
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
            f"  {c('status', BOLD + CYAN)}              Xem trạng thái đội ngũ Agents, Models & Skills của Project\n"
            f"  {c('list-skills', BOLD + CYAN)}         Liệt kê toàn bộ 150+ Skills đang có trên máy\n\n"
            f"{c('TÙY CHỌN (OPTIONS):', BOLD + YELLOW)}\n"
            f"  {c('-t, --target <path>', CYAN)}     Đường dẫn tới project/repo cần thiết lập (mặc định: `.`)\n"
            f"  {c('-y, --yes', CYAN)}               Khởi tạo tự động bằng Preset 5 Agents chuẩn (không hỏi đáp)\n"
            f"  {c('--goal <text>', CYAN)}           Mục tiêu chính của project (dùng kèm `--yes`)\n"
            f"  {c('--context <text>', CYAN)}        Ngữ cảnh kiến trúc của project (dùng kèm `--yes`)\n"
            f"  {c('--harnesses <list>', CYAN)}      Công cụ xuất cấu hình: `agy,codex,claude` (mặc định: cả 3)\n"
            f"  {c('--skill-mode <mode>', CYAN)}     Chế độ gắn skills: `symlink` | `copy` | `json-only`\n"
            f"  {c('--lang <en|vi>', CYAN)}          Ngôn ngữ giao diện CLI: `en` (Tiếng Anh, mặc định) hoặc `vi` (Tiếng Việt)\n"
            f"  {c('--dry-run', CYAN)}               Xem trước danh sách file sẽ sinh ra mà không ghi xuống ổ cứng\n"
            f"  {c('-h, --help', CYAN)}              Hiển thị bảng hướng dẫn này\n\n"
            f"{c('VÍ DỤ:', BOLD + YELLOW)}\n"
            f"  • Thiết lập đội AI cho một project       : {c('cd ~/project-example && agt', GREEN)}\n"
            f"  • Mở giao diện Tiếng Việt                : {c('cd ~/project-example && agt --lang vi', GREEN)}\n"
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
                ("preset", "Khởi tạo nhanh đội hình 5 Agents chuẩn cho 1 Project (Quick Preset)"),
                ("status", "Xem trạng thái đội ngũ AI & Skills của Project"),
                ("list-skills", "Tra cứu danh sách 150+ Skills đang có trên máy"),
                ("lang", "Switch CLI language to English (Chuyển sang Tiếng Anh)"),
                ("exit", "Thoát (Exit)"),
            ]
            prompt_title = "BẢNG ĐIỀU KHIỂN CHÍNH — Chọn tác vụ bạn muốn thực hiện"
        else:
            print(f"📍 Current working directory: {c(cwd_str, BOLD + GREEN)}")
            menu_opts = [
                ("wizard", "Configure Multi-Agent Team & Skills step-by-step (Interactive Wizard)"),
                ("preset", "Quick-initialize standard 5-Agent Team (Quick Preset)"),
                ("status", "Inspect active Agent Team & Skills status for a Project"),
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
        if action == "preset":
            proj = select_project_directory(target_path, projects_root)
            default_goal = (
                f"Phát triển, kiểm thử và duy trì {proj.name} với đội ngũ 5 Agents."
                if CURRENT_LANG == "vi"
                else f"Develop, test, and maintain {proj.name} with a 5-Agent team."
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

    parser = argparse.ArgumentParser(
        prog="agt",
        add_help=False,
        description="CLI Wizard (agt) to configure Multi-Agent teams & Skills for ~/Projects.",
    )
    parser.add_argument("--lang", type=str, default="en", choices=["en", "vi"], help="CLI language (en/vi)")
    parser.add_argument("--target", "-t", type=str, default=".", help="Target project/repo path")
    parser.add_argument("--yes", "-y", action="store_true", help="Non-interactive mode with standard preset")
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

    p_menu = subparsers.add_parser("menu", add_help=False, help="Open interactive dashboard menu")
    p_menu.add_argument("--lang", type=str, default=argparse.SUPPRESS, choices=["en", "vi"])
    p_menu.add_argument("--target", "-t", type=str, default=argparse.SUPPRESS, help="Target project/repo path")

    args = parser.parse_args()
    CURRENT_LANG = lang if "--lang" in raw_argv else getattr(args, "lang", "en")
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
