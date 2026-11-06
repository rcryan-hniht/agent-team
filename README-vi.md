# 🤖 `agt` (`agent-team`) — Công cụ CLI Thiết lập Đội ngũ AI & Skills

[English](./README.md) | **Tiếng Việt**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg)](https://www.python.org/)

`agt` là công cụ CLI tương tác (không phụ thuộc thư viện ngoài) giúp bạn thiết lập một **Đội ngũ AI (Multi-Agent Team)** gồm **Orchestrator**, **Reviewer**, **Implementer**, **Searcher**, **Committer** (hoặc bất kỳ vai trò tùy chỉnh nào) cho từng dự án trong `~/Projects`, đồng thời đảm bảo `AGENTS.md` luôn gọn gàng **dưới 150 dòng (< 150 lines)**.

Khi chạy lệnh `agt`, giao diện dòng lệnh Tiếng Việt sẽ hỏi từng bước về:
- **Nhiệm vụ riêng (Mission)** của từng agent
- **Provider & Model** (`gemini-4-argon-high`, `claude-opus-5-5-medium`, `gemini-3.1-pro-high`, `gemini-3.8-flash-high`, `gpt-6-astra`, `gpt-6.1-sol`, `gpt-6-sol`, `gpt-6-luna`...)
- **Ngữ cảnh (Context/Scope)** & **Mục tiêu/Tiêu chí hoàn thành (Completion Criteria)**
- **Quyền công cụ** (`Read-Only` vs `Read+Write+Bash`, `Subagent Dispatch`, `Workspace Isolation`)
- **Tự động quét & gắn Skills** từ kho skills sẵn có trên máy của bạn (`~/.gemini/config/plugins/*`, `~/Projects/Hephaestus/.agents/skills/*`, `superpowers`, `mattpocock-skills`, `ponytail`, `ui-ux-pro-max`, `taste-skill`, `native_swarm`...) vào từng repo.

---

## 1. Các Repo Mã Nguồn Mở Liên Quan (Tham khảo)

Nếu bạn muốn tham khảo thêm các bộ sưu tập mẫu từ cộng đồng:
1. **[`wshobson/agents`](https://github.com/wshobson/agents)**: Kho sưu tập hơn 100+ subagents và skills đa nền tảng (Claude Code, Codex, Antigravity, Cursor).
2. **[`obra/superpowers`](https://github.com/obra/superpowers)** *(Đã cài sẵn trên máy bạn tại `~/.gemini/config/plugins/superpowers`)*: Hệ thống workflow chuẩn (`brainstorming`, `writing-plans`, `subagent-driven-development`, `dispatching-parallel-agents`, `test-driven-development`).
3. **[`mattpocock/skills`](https://github.com/mattpocock/skills)** *(Đã cài sẵn tại `~/.gemini/config/plugins/mattpocock-skills`)*: Bộ kỹ năng chuyên sâu cho `code-review` (song song 2 trục Spec & Standards), `tdd`, `codebase-design`, `writing-for-agents`.
4. **[`VoltAgent/awesome-claude-code-subagents`](https://github.com/VoltAgent/awesome-claude-code-subagents)**: Danh sách các mẫu `.claude/agents/*.md` chia theo từng vai trò kỹ thuật.
5. **[`intellectronica/ruler`](https://github.com/intellectronica/ruler)**: Công cụ đồng bộ file quy tắc ra `AGENTS.md`, `CLAUDE.md`.

> **Điểm khác biệt của `agt`**: Thay vì chỉ chép các mẫu tĩnh, `agt` là **Interactive Wizard** có giao diện Tiếng Việt trực quan, đặt câu hỏi riêng cho từng dự án trong `~/Projects`, kết nối trực tiếp với kho **150+ Skills đang cài trên máy bạn**, giữ `AGENTS.md` luôn **< 150 lines**, và xuất đồng thời cả 3 chuẩn (`agy`, `codex`, `claude`) để bạn điều phối ngay trong công cụ đang mở.

---

## 2. Cách Sử Dụng Nhanh

Công cụ được liên kết vào `~/.local/bin/agt`. Bạn có thể gõ lệnh từ bất kỳ đâu:

### A. Mở Menu Giao Diện Dòng Lệnh Tiếng Việt hoặc Chạy Wizard
```bash
cd ~/Projects
agt
```
- Khi gõ `agt`, menu chính bằng Tiếng Việt sẽ hiện ra (Thiết lập đội ngũ AI theo từng bước, Tạo nhanh theo Preset, Xem trạng thái Project, Tra cứu kho Skills, hoặc Đổi ngôn ngữ `Tiếng Việt / English`).
- Nếu bạn gõ tại `~/Projects`, CLI sẽ liệt kê toàn bộ các repo con (`Act2Morse`, `Hephaestus`, `Orpheus`, `uav-agri-autonomy`, v.v.) để bạn chọn repo muốn thiết lập.
- Nếu bạn `cd ~/Projects/<tên-repo>` rồi gõ `agt`, CLI sẽ tự động nhận diện ngôn ngữ/framework của repo đó và hỏi từng bước thiết lập.

### B. Tạo nhanh bằng Preset (Không cần hỏi đáp)
```bash
agt init --target ~/Projects/Orpheus --yes \
  --goal "Xây dựng và tối ưu hệ thống với đội ngũ 5 agents"
```

### C. Xem danh sách toàn bộ Skills trên máy & Trạng thái đội AI của một Repo
```bash
# Liệt kê tất cả skills đang có trên máy theo từng plugin
agt list-skills

# Kiểm tra đội hình AI và skills đã gắn trong một repo
agt status --target ~/Projects/Orpheus

# Chuyển đổi ngôn ngữ giao diện CLI (vi / en)
agt --lang vi
agt --lang en
```

---

## 3. Cấu Trúc File Được Sinh Ra Tự Động Cho Mỗi Project

```text
<project-root>/
├── AGENTS.md                                  # Chuẩn chung (< 150 dòng) cho OpenAI Codex, Antigravity, Claude
├── CLAUDE.md                                  # Entrypoint cho Anthropic Claude Code
├── .agents/
│   ├── README.md                              # Bảng ánh xạ đầy đủ Role ↔ Model (Agy & Codex) ↔ Skills
│   ├── agents.json                            # Danh mục đăng ký subagents cho Antigravity (agy)
│   ├── skills.json                            # Đăng ký & lọc (include_only) các skills cho repo
│   ├── team-config.json                       # Lưu cấu hình để chỉnh sửa lại bất cứ lúc nào
│   ├── rules/
│   │   └── commit-restrictions.md             # (Tùy chọn) Chặn commit nhầm AGENTS.md / SKILL.md
│   ├── agents/
│   │   ├── orchestrator/ (agent.md, agent.toml)
│   │   ├── reviewer/ (agent.md, agent.toml)
│   │   ├── implementer/ (agent.md, agent.toml)
│   │   ├── searcher/ (agent.md, agent.toml)
│   │   └── committer/ (agent.md, agent.toml)
│   └── skills/                                # Các skills được symlink hoặc copy vào dự án
├── .claude/
│   └── agents/
│       ├── orchestrator.md                    # Subagent YAML frontmatter chuẩn Claude Code
│       ├── reviewer.md
│       ├── implementer.md
│       ├── searcher.md
│       └── committer.md
└── .codex/
    └── config.toml                            # Cấu hình [agents.<role>] chuẩn cho OpenAI Codex CLI
```

---

## 4. Giấy phép (License)

Phát hành dưới giấy phép [MIT License](./LICENSE).
