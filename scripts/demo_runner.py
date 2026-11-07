#!/usr/bin/env python3
"""
agt Terminal Demo Runner
Executes an authentic, timed CLI showcase inside a native terminal (e.g. Ghostty).

Features demonstrated:
  • 8-Role Multi-Agent Team Catalog & Mascot Pixel Art (with southern rockhopper penguin)
  • Realtime Token Velocity Telemetry & 15m Sparklines
  • System Theme Auto-Sync (Dark Mode cool neon glow vs Light Mode warm rosewood accents)
  • Model & Cross-Provider Fallback Chains
  • Scaffolding Presets

Timeline (~47s total duration):
  • 00:00 - 00:02 (2.0s): Warm-up buffer
  • 00:02 - 00:07 (5.0s): agt --help (Command catalog & options)
  • 00:07 - 00:15 (8.0s): clear -> agt status (8 mascots & fallback chains)
  • 00:15 - 00:24 (9.0s): clear -> agt ps --once (Dark Theme: live telemetry & task occupancy)
  • 00:24 - 00:34 (10.0s): clear -> Theme Auto-Sync Showcase
                          AGT_THEME=light agt ps --once --active "designer,implementer"
                          (Light Theme: warm rosewood pink/red active accents & lavender grey idle sprites)
  • 00:34 - 00:40 (6.0s): clear -> agt fallback (Cross-provider model chains)
  • 00:40 - 00:44 (4.0s): clear -> agt init -h (Fast scaffolding options)
  • 00:44 - 00:47 (3.0s): Freeze outro buffer
"""

import os
import random
import subprocess
import sys
import time
from pathlib import Path

AGT_BIN = "/home/killua/.local/bin/agt"
PROJECT_DIR = "/home/killua/Projects/agent-team"
PROMPT = "\033[01;32mkillua@resolute\033[00m:\033[01;34m~/Projects/agent-team\033[00m$ "
CLEAR_SCREEN = "\033[2J\033[3J\033[H"


def typewriter(text: str, min_delay: float = 0.045, max_delay: float = 0.075) -> None:
    """Simulate natural human typing into the terminal."""
    for ch in text:
        sys.stdout.write(ch)
        sys.stdout.flush()
        time.sleep(random.uniform(min_delay, max_delay))


def wait_until(t_start: float, target_offset: float) -> None:
    """Hold execution until the target offset from t_start is reached."""
    now = time.monotonic() - t_start
    remaining = target_offset - now
    if remaining > 0:
        time.sleep(remaining)


def run_command(
    cmd: list[str],
    t_start: float,
    stdin_input: str | None = None,
    extra_env: dict[str, str] | None = None,
) -> None:
    """Run command preserving terminal formatting and ANSI codes."""
    env = os.environ.copy()
    env["COLORTERM"] = "truecolor"
    env["TERM"] = "xterm-256color"
    env["FORCE_COLOR"] = "1"
    if extra_env:
        env.update(extra_env)

    kwargs = {
        "cwd": PROJECT_DIR,
        "env": env,
        "check": True,
    }
    if stdin_input is not None:
        kwargs["input"] = stdin_input
        kwargs["text"] = True

    subprocess.run(cmd, **kwargs)


def main() -> None:
    if not Path(AGT_BIN).exists():
        sys.stderr.write(f"Error: {AGT_BIN} not found.\n")
        sys.exit(1)

    t0 = time.monotonic()

    # -------------------------------------------------------------
    # 00:00 - 00:02 (2.0s): Warm-up buffer
    # -------------------------------------------------------------
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.write(PROMPT)
    sys.stdout.flush()
    wait_until(t0, 2.0)

    # -------------------------------------------------------------
    # 00:02 - 00:07 (5.0s): agt --help
    # -------------------------------------------------------------
    typewriter("agt --help")
    time.sleep(0.12)
    sys.stdout.write("\n")
    sys.stdout.flush()

    run_command([AGT_BIN, "--help"], t0)
    sys.stdout.write("\n" + PROMPT)
    sys.stdout.flush()
    wait_until(t0, 7.0)

    # -------------------------------------------------------------
    # 00:07 - 00:15 (8.0s): clear -> agt status
    # -------------------------------------------------------------
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.write(PROMPT)
    sys.stdout.flush()
    time.sleep(0.08)

    typewriter("agt status")
    time.sleep(0.12)
    sys.stdout.write("\n")
    sys.stdout.flush()

    run_command([AGT_BIN, "status"], t0)
    sys.stdout.write("\n" + PROMPT)
    sys.stdout.flush()
    wait_until(t0, 15.0)

    # -------------------------------------------------------------
    # 00:15 - 00:24 (9.0s): clear -> agt ps --once (Dark Theme)
    # -------------------------------------------------------------
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.write(PROMPT)
    sys.stdout.flush()
    time.sleep(0.08)

    typewriter("agt ps --once")
    time.sleep(0.12)
    sys.stdout.write("\n")
    sys.stdout.flush()

    run_command([AGT_BIN, "ps", "--once"], t0, extra_env={"AGT_THEME": "dark"})
    sys.stdout.write("\n" + PROMPT)
    sys.stdout.flush()
    wait_until(t0, 24.0)

    # -------------------------------------------------------------
    # 00:24 - 00:34 (10.0s): clear -> Theme Auto-Sync Showcase (Light Theme)
    # -------------------------------------------------------------
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.write(PROMPT)
    sys.stdout.flush()
    time.sleep(0.08)

    typewriter('AGT_THEME=light agt ps --once --active "designer,implementer"')
    time.sleep(0.12)
    sys.stdout.write("\n")
    sys.stdout.flush()

    run_command(
        [AGT_BIN, "ps", "--once", "--active", "designer,implementer"],
        t0,
        extra_env={"AGT_THEME": "light"},
    )
    sys.stdout.write("\n" + PROMPT)
    sys.stdout.flush()
    wait_until(t0, 34.0)

    # -------------------------------------------------------------
    # 00:34 - 00:40 (6.0s): clear -> agt fallback
    # -------------------------------------------------------------
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.write(PROMPT)
    sys.stdout.flush()
    time.sleep(0.08)

    typewriter("agt fallback")
    time.sleep(0.12)
    sys.stdout.write("\n")
    sys.stdout.flush()

    # Option 4: exit fallback interactive prompt cleanly
    run_command([AGT_BIN, "fallback"], t0, stdin_input="4\n")
    sys.stdout.write("\n" + PROMPT)
    sys.stdout.flush()
    wait_until(t0, 40.0)

    # -------------------------------------------------------------
    # 00:40 - 00:44 (4.0s): clear -> agt init -h
    # -------------------------------------------------------------
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.write(PROMPT)
    sys.stdout.flush()
    time.sleep(0.08)

    typewriter("agt init -h")
    time.sleep(0.12)
    sys.stdout.write("\n")
    sys.stdout.flush()

    run_command([AGT_BIN, "init", "-h"], t0)
    sys.stdout.write("\n" + PROMPT)
    sys.stdout.flush()
    wait_until(t0, 44.0)

    # -------------------------------------------------------------
    # 00:44 - 00:47 (3.0s): Freeze outro buffer
    # -------------------------------------------------------------
    wait_until(t0, 47.0)


if __name__ == "__main__":
    main()
