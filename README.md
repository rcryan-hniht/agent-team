# 🤖 `agt` — Multi-Agent Team & Skills CLI Generator

Công cụ CLI tương tác (`agt`) giúp bạn thiết lập một **Đội ngũ AI (Multi-Agent Team)** gồm **Orchestrator**, **Reviewer**, **Implementer**, **Searcher**, **Committer** (hoặc bất kỳ vai trò tùy chỉnh nào) cho từng dự án trong `~/Projects`, đồng thời đảm bảo `AGENTS.md` luôn gọn gàng **dưới 150 dòng (< 150 lines)**.

Khi chạy lệnh, công cụ sẽ hỏi chi tiết về:
- **Nhiệm vụ riêng (Mission)** của từng agent
- **Provider & Model** (`inherit`, `google/pro/flash`, `anthropic/opus/sonnet/haiku`, `openai/gpt-5-codex/o3`)
- **Ngữ cảnh (Context/Scope)** & **Mục tiêu/Tiêu chí hoàn thành (Completion Criteria)**
- **Quyền công cụ** (`Read-Only` vs `Read+Write+Bash`, `Subagent Dispatch`, `Workspace Isolation`)
- **Tự động quét & gắn Skills** từ kho skills sẵn có trên máy của bạn (`~/.gemini/config/plugins/*`, `superpowers`, `mattpocock-skills`, `ponytail`, `ui-ux-pro-max`, `taste-skill`, `native_swarm`...) vào từng repo.

---

## 1. Các Repo Mã Nguồn Mở Liên Quan (Tham khảo)

Nếu bạn muốn tham khảo thêm các bộ sưu tập mẫu từ cộng đồng:
1. **[`wshobson/agents`](https://github.com/wshobson/agents)**: Kho sưu tập hơn 100+ subagents và skills đa nền tảng (Claude Code, Codex, Antigravity, Cursor).
2. **[`obra/superpowers`](https://github.com/obra/superpowers)** *(Đã cài sẵn trên máy bạn tại `~/.gemini/config/plugins/superpowers`)*: Hệ thống workflow chuẩn (`brainstorming`, `writing-plans`, `subagent-driven-development`, `dispatching-parallel-agents`, `test-driven-development`).
3. **[`mattpocock/skills`](https://github.com/mattpocock/skills)** *(Đã cài sẵn tại `~/.gemini/config/plugins/mattpocock-skills`)*: Bộ kỹ năng chuyên sâu cho `code-review` (song song 2 trục Spec & Standards), `tdd`, `codebase-design`, `writing-for-agents`.
4. **[`VoltAgent/awesome-claude-code-subagents`](https://github.com/VoltAgent/awesome-claude-code-subagents)**: Danh sách các mẫu `.claude/agents/*.md` chia theo từng vai trò kỹ thuật.
5. **[`intellectronica/ruler`](https://github.com/intellectronica/ruler)**: Công cụ đồng bộ file quy tắc ra `AGENTS.md`, `CLAUDE.md`.

> **Điểm khác biệt của `agt`**: Thay vì chỉ chép các mẫu tĩnh, `agt` là **Interactive Wizard** đặt câu hỏi riêng cho từng dự án trong `~/Projects`, kết nối trực tiếp với kho **150+ Skills đang cài trên máy bạn**, giữ `AGENTS.md` luôn **< 150 lines**, và xuất đồng thời cả 3 chuẩn (`agy`, `codex`, `claude`) để bạn điều phối ngay trong công cụ đang mở.

---

## 2. Cách Sử Dụng Nhanh

Công cụ đã được liên kết vào `~/.local/bin/agt`. Bạn có thể gõ lệnh từ bất kỳ đâu:

### A. Chạy Interactive Wizard ngay trong `~/Projects` hoặc trong một Repo
```bash
cd ~/Projects
agt
```
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
```

---

## 3. Cấu Trúc File Được Sinh Ra Tự Động Cho Mỗi Project

```text
<project-root>/
├── AGENTS.md                                  # Chuẩn chung (OpenAI Codex, Antigravity, Claude)
├── GEMINI.md                                  # Entrypoint cho Google Antigravity (agy)
├── CLAUDE.md                                  # Entrypoint cho Anthropic Claude Code
├── .agents/
│   ├── team-config.json                       # Lưu cấu hình để chỉnh sửa lại bất cứ lúc nào
│   ├── skills.json                            # Đăng ký & lọc (include_only) các skills cho repo
│   ├── rules/
│   │   └── agent-team.md                      # Quy tắc phân quyền & điều phối đội ngũ
│   ├── subagents/
│   │   ├── orchestrator.json / .md            # Payload chuẩn cho define_subagent & invoke_subagent
│   │   ├── searcher.json / .md
│   │   ├── implementer.json / .md
│   │   └── reviewer.json / .md
│   └── skills/
│       └── team-orchestrator/
│           └── SKILL.md                       # Skill tự động khởi chạy đội hình trong agy/claude
├── .claude/
│   └── agents/
│       ├── orchestrator.md                    # Subagent YAML frontmatter chuẩn Claude Code
│       ├── searcher.md
│       ├── implementer.md
│       └── reviewer.md
└── .codex/
    └── config.toml                            # Profiles (model, sandbox, approval) cho OpenAI Codex CLI
```
