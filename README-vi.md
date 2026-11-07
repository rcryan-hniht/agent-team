<div align="center">
  <img src="./assets/demo.gif" alt="agt (agent-team) — Bản demo CLI Đội ngũ Multi-Agent" width="100%" />
  <br />
  <br />
  <p>
    <a href="./README.md">English</a> | <strong>Tiếng Việt</strong>
  </p>
  <p>
    <a href="./LICENSE"><img src="https://img.shields.io/badge/License-MIT-00F0FF.svg?style=flat-square&labelColor=0D1117" alt="License: MIT" /></a>
    <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-10B981.svg?style=flat-square&labelColor=0D1117" alt="Python 3.10+" /></a>
    <img src="https://img.shields.io/badge/AGENTS.md-%3C%20150%20D%C3%B2ng-F59E0B.svg?style=flat-square&labelColor=0D1117" alt="AGENTS.md < 150 Dòng" />
    <img src="https://img.shields.io/badge/Harnesses-.agents%20%7C%20.codex%20%7C%20.claude-38BDF8.svg?style=flat-square&labelColor=0D1117" alt="Harnesses" />
  </p>
</div>

`agt` (`agent-team`) là công cụ dòng lệnh (CLI wizard) thuần Python (không cần cài thêm thư viện ngoài), tự động thiết lập **Đội ngũ AI 2 Pha 8 Vai Trò** (**lead-architect**, **lead-critic**, **orchestrator**, **reviewer**, **designer**, **implementer**, **searcher**, **committer**) tương thích đồng thời cả 3 nền tảng **Google Antigravity (`agy`)**, **OpenAI Codex (`codex`)**, và **Anthropic Claude Code (`claude`)**, đồng thời giữ file chỉ dẫn `AGENTS.md` luôn **gọn dưới 150 dòng**.

---

## ⚡ Cài đặt nhanh trong 10 giây

Cài đặt `agt` vào `~/.local/bin/agt` bằng 1 lệnh duy nhất (yêu cầu Python 3.10+):

```bash
curl -fsSL https://raw.githubusercontent.com/rcryan-hniht/agent-team/main/install.sh | bash
```

---

## 🎮 Các lệnh thiết yếu

| Lệnh | Ý nghĩa |
| :--- | :--- |
| `agt` | Mở menu tương tác / TUI Dashboard (mặc định Tiếng Anh, `--lang vi` cho Tiếng Việt) |
| `agt init -y` | Khởi tạo tự động đội ngũ 8 vai trò chuẩn bằng Preset (không cần hỏi đáp) |
| `agt ps` | Giám sát trực tiếp (chu kỳ 0.5s siêu nhanh, cuộn phím nvim `j`/`k`, đo tốc độ token) |
| `agt status` | Kiểm tra trạng thái đội hình AI, model và skills đang gắn trong repo |
| `agt fallback` | Quản lý hoặc lùi model dự phòng khi hết quota (`--step-down <role>`) |
| `agt clean -y` | Dọn dẹp / xóa nhanh toàn bộ cấu hình AI agents khỏi repo |

---

## 🤖 Đội ngũ 8 Vai trò & Mascot

| Vai trò | Linh vật | Model mặc định (`agy`) | Model mặc định (`codex`) | Pha | Mục tiêu chính |
| :--- | :---: | :--- | :--- | :---: | :--- |
| **`lead-architect`** | 🐋 | `gemini-4-argon-high` / `claude-opus-5-5-medium` | `gpt-6-astra` (`high`) | Pha 1 | Đề xuất kiến trúc tổng thể, đặc tả kỹ thuật & phân rã task |
| **`lead-critic`** | 🐋 | `gemini-3.1-pro-high` / `claude-opus-5-5-medium` | `gpt-6.1-sol` (`xhigh`) | Pha 1 | Tranh biện 2 vòng, stress-test giả định & kiểm định YAGNI |
| **`orchestrator`** | 🐙 | `gemini-4-argon-high` / `claude-opus-5-5-medium` | `gpt-6-astra` (`high`) | Pha 2 | Điều phối tổng thể các worker subagents & kiểm định tích hợp |
| **`reviewer`** | 🦈 | `gemini-3.1-pro-high` | `gpt-6.1-sol` (`xhigh`) | Pha 2 | Đánh giá độc lập 2 trục: Chuẩn mã nguồn & Đáp ứng Spec |
| **`designer`** | 🐧 | `gemini-3.8-flash-high` | `gpt-6-sol` (`xhigh`) | Pha 2 | Thiết kế UI/UX & Style Anti-Slop theo chuẩn thẩm mỹ |
| **`implementer`** | 🦈 | `gemini-3.8-flash-high` | `gpt-6-sol` (`xhigh`) | Pha 2 | Viết code tối giản & kiểm thử TDD (Red-Green-Refactor) |
| **`searcher`** | 🐟 | `gemini-3.8-flash-medium` | `gpt-6-luna` (`medium`) | Pha 2 | Trinh sát codebase & tra cứu tài liệu nhanh |
| **`committer`** | ⭐ | `gemini-3.7-flash` | `gpt-6-luna` (`low`) | Pha 2 | Đóng gói Conventional Git Commits nguyên tử |

---

## 💡 Điểm nổi bật kỹ thuật

- **Tự động đồng bộ Theme (Auto-Sync System Theme)**: Linh vật pixel art và huy hiệu tự động biến đổi màu sắc theo theme hệ thống Dark / Light (Dark style: ánh neon mát cyberpunk; Light style: sắc ấm Rosewood Garnet hồng phấn/đỏ dịu mắt).
- **Giám sát thời gian thực (`agt ps`)**: Chu kỳ làm mới mặc định **0.5 giây** chống giật màn hình (double-buffering), điều hướng kiểu nvim (`j`/`k`/`d`/`u`), kèm thanh đo tốc độ tiêu thụ Token Velocity (TPM) 15 phút dạng sparkline `[ ▂▃▄▅▆▇█]`.
- **Giữ ngữ cảnh gọn gàng**: `AGENTS.md` ở thư mục gốc luôn dưới 150 dòng để tiết kiệm cửa sổ ngữ cảnh (context window) của mô hình.
- **Điều phối Host-Native**: Hoạt động hoàn toàn dựa trên cơ chế subagent sẵn có của công cụ host (`agy`, `codex`, `claude`), không chạy daemon ngầm gây tốn RAM/CPU.
- **Chuỗi lùi Fallback linh hoạt**: Tự động chuyển đổi giữa Gemini, Claude và OpenAI khi chạm hạn mức gọi API (`agt fallback --step-down <role>`).

---

## 📂 Cấu trúc thư mục sinh ra

```text
<project-root>/
├── AGENTS.md             # File chỉ dẫn chung gọn gàng (< 150 dòng)
├── CLAUDE.md             # Điểm vào cho Claude Code (trỏ về @AGENTS.md)
├── .agents/
│   ├── README.md         # Bảng chi tiết model, vai trò & danh mục skills
│   ├── agents.json       # Danh mục subagents cho Antigravity (agy)
│   ├── skills.json       # Khai báo các skills được kích hoạt
│   ├── agents/           # Cấu hình từng agent (agent.md, agent.toml)
│   ├── subagents/        # Payload cho define_subagent / invoke_subagent
│   └── skills/           # Liên kết mềm (symlink) tới kho skills cục bộ
├── .claude/agents/       # Cấu hình subagents cho Claude Code
└── .codex/config.toml    # Cấu hình multi-agent cho OpenAI Codex
```

---

## 🔗 Các dự án mã nguồn mở liên quan

- [`wshobson/agents`](https://github.com/wshobson/agents) — Bộ sưu tập multi-harness agents & plugins.
- [`obra/superpowers`](https://github.com/obra/superpowers) — Kỹ năng workflow agentic (`brainstorming`, `writing-plans`, `subagent-driven-development`).
- [`mattpocock/skills`](https://github.com/mattpocock/skills) — Thiết kế module, TDD, và review mã 2 trục.
- [`VoltAgent/awesome-claude-code-subagents`](https://github.com/VoltAgent/awesome-claude-code-subagents) — Thư viện mẫu `.claude/agents/`.
- [`intellectronica/ruler`](https://github.com/intellectronica/ruler) — Tiện ích đồng bộ hóa rules đa nền tảng.

---

## 📄 Bản quyền (License)

Phát hành theo giấy phép [MIT License](./LICENSE).
