#!/usr/bin/env python3
"""
agt 30-Second Terminal Demo Runner
Executes an authentic, timed CLI showcase inside a native terminal (e.g. Ghostty).

Timeline:
  • 00:00 - 00:02 (2.0s): Warm-up buffer
  • 00:02 - 00:06 (4.0s): agt --help
  • 00:06 - 00:14 (8.0s): clear -> agt status
  • 00:14 - 00:22 (8.0s): clear -> agt ps --once
  • 00:22 - 00:27 (5.0s): clear -> agt fallback
  • 00:27 - 00:30 (3.0s): clear -> agt init -h
  • 00:30 - 00:33 (3.0s): Freeze outro buffer
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
) -> None:
    """Run command preserving terminal formatting and ANSI codes."""
    env = os.environ.copy()
    env["COLORTERM"] = "truecolor"
    env["TERM"] = "xterm-256color"
    env["FORCE_COLOR"] = "1"

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
    # 00:02 - 00:06 (4.0s): agt --help
    # -------------------------------------------------------------
    typewriter("agt --help")
    time.sleep(0.12)
    sys.stdout.write("\n")
    sys.stdout.flush()

    run_command([AGT_BIN, "--help"], t0)
    sys.stdout.write("\n" + PROMPT)
    sys.stdout.flush()
    wait_until(t0, 6.0)

    # -------------------------------------------------------------
    # 00:06 - 00:14 (8.0s): clear -> agt status
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
    wait_until(t0, 14.0)

    # -------------------------------------------------------------
    # 00:14 - 00:22 (8.0s): clear -> agt ps --once
    # -------------------------------------------------------------
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.write(PROMPT)
    sys.stdout.flush()
    time.sleep(0.08)

    typewriter("agt ps --once")
    time.sleep(0.12)
    sys.stdout.write("\n")
    sys.stdout.flush()

    run_command([AGT_BIN, "ps", "--once"], t0)
    sys.stdout.write("\n" + PROMPT)
    sys.stdout.flush()
    wait_until(t0, 22.0)

    # -------------------------------------------------------------
    # 00:22 - 00:27 (5.0s): clear -> agt fallback
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
    wait_until(t0, 27.0)

    # -------------------------------------------------------------
    # 00:27 - 00:30 (3.0s): clear -> agt init -h
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
    wait_until(t0, 30.0)

    # -------------------------------------------------------------
    # 00:30 - 00:33 (3.0s): Freeze outro buffer
    # -------------------------------------------------------------
    wait_until(t0, 33.0)


if __name__ == "__main__":
    main()
