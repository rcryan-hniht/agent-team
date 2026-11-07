import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import agent_team


class TestTokenTelemetry(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.brain_root = Path(self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _create_session_transcript(self, session_id: str, records: list) -> Path:
        sess_dir = self.brain_root / session_id / ".system_generated" / "logs"
        sess_dir.mkdir(parents=True, exist_ok=True)
        tr_file = sess_dir / "transcript.jsonl"
        with open(tr_file, "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")
        return tr_file

    def test_empty_or_nonexistent_brain_returns_zero_snapshot(self):
        empty_brain = self.brain_root / "nonexistent"
        snapshot = agent_team.collect_token_telemetry(brain_root=empty_brain, window_minutes=15)
        self.assertEqual(snapshot.window_minutes, 15)
        self.assertEqual(snapshot.current_tpm, 0)
        self.assertEqual(snapshot.peak_tpm, 0)
        self.assertEqual(snapshot.avg_tpm, 0)
        self.assertEqual(snapshot.total_input, 0)
        self.assertEqual(snapshot.total_output, 0)
        self.assertEqual(snapshot.total_cache_read, 0)
        self.assertEqual(snapshot.cache_hit_rate, 0.0)
        self.assertEqual(snapshot.active_sessions_count, 0)
        self.assertEqual(len(snapshot.buckets_tpm), 15)
        self.assertEqual(snapshot.sparkline_15.strip(), "")

    def test_fresh_throughput_excludes_cache_read_from_tpm(self):
        now = datetime(2026, 11, 8, 2, 0, 0, tzinfo=timezone.utc)
        record = {
            "source": "MODEL",
            "created_at": "2026-11-08T01:59:30Z",
            "input_tokens": 2000,
            "output_tokens": 500,
            "cache_read_tokens": 120000,
        }
        self._create_session_transcript("sess-1", [record])

        snapshot = agent_team.collect_token_telemetry(brain_root=self.brain_root, window_minutes=15, now_dt=now)
        # Fresh throughput = 2000 + 500 = 2500 (NOT 122500!)
        self.assertEqual(snapshot.peak_tpm, 2500)
        self.assertEqual(snapshot.current_tpm, 2500)
        self.assertEqual(snapshot.total_input, 2000)
        self.assertEqual(snapshot.total_output, 500)
        self.assertEqual(snapshot.total_cache_read, 120000)
        # Cache hit rate = 120000 / (2000 + 120000) * 100 = 98.36% -> 98.4%
        self.assertAlmostEqual(snapshot.cache_hit_rate, 98.4, places=1)

    def test_tail_jsonl_lines_safely_drops_partial_first_line(self):
        log_file = self.brain_root / "test.jsonl"
        # Write 3 lines. When seeking from middle of line 1, line 1 should be dropped.
        l1 = json.dumps({"source": "USER", "text": "A" * 500}) + "\n"
        l2 = json.dumps({"source": "MODEL", "step": 1}) + "\n"
        l3 = json.dumps({"source": "MODEL", "step": 2}) + "\n"
        log_file.write_text(l1 + l2 + l3, encoding="utf-8")

        # Seek with a small max_bytes that falls inside l1
        lines = agent_team.tail_jsonl_lines(log_file, max_bytes=len(l2) + len(l3) + 50, max_lines=10)
        self.assertEqual(len(lines), 2)
        parsed = [json.loads(x) for x in lines]
        self.assertEqual(parsed[0]["step"], 1)
        self.assertEqual(parsed[1]["step"], 2)

    def test_15_minute_rolling_window_and_chronological_order(self):
        now = datetime(2026, 11, 8, 2, 0, 0, tzinfo=timezone.utc)
        records = [
            # 0.5m ago (bucket 14 - rightmost / current)
            {"source": "MODEL", "created_at": (now - timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ"), "input_tokens": 100, "output_tokens": 50},
            # 5m ago (bucket 9)
            {"source": "MODEL", "created_at": (now - timedelta(minutes=5, seconds=10)).strftime("%Y-%m-%dT%H:%M:%SZ"), "input_tokens": 300, "output_tokens": 100},
            # 14m ago (bucket 0 - leftmost)
            {"source": "MODEL", "created_at": (now - timedelta(minutes=14, seconds=20)).strftime("%Y-%m-%dT%H:%M:%SZ"), "input_tokens": 50, "output_tokens": 50},
            # 16m ago (out of 15m window - ignored)
            {"source": "MODEL", "created_at": (now - timedelta(minutes=16)).strftime("%Y-%m-%dT%H:%M:%SZ"), "input_tokens": 1000, "output_tokens": 1000},
        ]
        self._create_session_transcript("sess-time", records)

        snapshot = agent_team.collect_token_telemetry(brain_root=self.brain_root, window_minutes=15, now_dt=now)
        # Bucket 0 (14m ago): 50 + 50 = 100
        self.assertEqual(snapshot.buckets_tpm[0], 100)
        # Bucket 9 (5m ago): 300 + 100 = 400
        self.assertEqual(snapshot.buckets_tpm[9], 400)
        # Bucket 14 (now): 100 + 50 = 150
        self.assertEqual(snapshot.buckets_tpm[14], 150)
        # Total input within 15m window = 100 + 300 + 50 = 450 (16m ago is excluded)
        self.assertEqual(snapshot.total_input, 450)

    @patch("sys.stdout.isatty", return_value=True)
    def test_render_token_dashboard_compact_mode_on_narrow_terminal(self, _mock_isatty):
        now = datetime(2026, 11, 8, 2, 0, 0, tzinfo=timezone.utc)
        self._create_session_transcript("sess-1", [
            {"source": "MODEL", "created_at": (now - timedelta(seconds=20)).strftime("%Y-%m-%dT%H:%M:%SZ"), "input_tokens": 5000, "output_tokens": 1000, "cache_read_tokens": 20000}
        ])
        snapshot = agent_team.collect_token_telemetry(brain_root=self.brain_root, window_minutes=15, now_dt=now)

        # On narrow terminal (term_w = 80)
        lines_80 = agent_team.render_token_dashboard(snapshot, theme="dark", term_w=80)
        self.assertTrue(lines_80)
        for line in lines_80:
            vis_len = agent_team._visible_len(line)
            self.assertLessEqual(vis_len, 78, f"Line too long for 80-col terminal: {vis_len} chars -> {line}")

        # On wide terminal (term_w = 115)
        lines_115 = agent_team.render_token_dashboard(snapshot, theme="dark", term_w=115)
        self.assertTrue(lines_115)
        self.assertTrue(any("Velocity (15m):" in l for l in lines_115))

    @patch("sys.stdout.isatty", return_value=True)
    def test_render_ps_view_integrates_telemetry_below_active_occupancy(self, _mock_isatty):
        with (
            patch.object(agent_team, "get_live_os_procs", return_value=[]),
            patch.object(agent_team, "detect_live_agent_occupancy", return_value=({"lead-architect": "Planning"}, [])),
        ):
            view = agent_team.render_ps_view(Path("."))

        lines = view.splitlines()
        occupancy_idx = next(i for i, l in enumerate(lines) if "Active Task Occupancy" in l or "Tác Vụ Đang Chiếm Giữ" in l)
        os_proc_idx = next(i for i, l in enumerate(lines) if "OS Processes" in l or "Tiến trình OS" in l)
        telemetry_idx = next(i for i, l in enumerate(lines) if "Token Velocity" in l or "Token Telemetry" in l or "Tốc Độ Tiêu Thụ Token" in l or "Đo lường Token" in l)

        self.assertGreater(telemetry_idx, occupancy_idx, "Telemetry must be placed below Active Task Occupancy")
        self.assertLess(telemetry_idx, os_proc_idx, "Telemetry must be placed before Live OS Processes")


if __name__ == "__main__":
    unittest.main()
