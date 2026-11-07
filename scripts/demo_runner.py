#!/usr/bin/env python3
"""
agt Production 33-Second Terminal Demo Runner
Executes an authentic, timed CLI workflow walkthrough inside a native terminal (e.g. Ghostty).

Workflow Timeline (~33s total duration):
  • Frame 0 / 00:00 - 00:05 (5.0s): Step 1: agt status (Instant hero render: 8 Mascots, Active Provider, Models & Skills)
  • 00:05 - 00:11 (6.0s): Step 2: agt init -t /tmp/demo-sandbox -y (Instant Multi-Harness Scaffolding)
  • 00:11 - 00:18 (7.0s): Step 3A: agt ps --once (Dark Theme: Real-time telemetry, 0.5s monitor, 'working' status)
  • 00:18 - 00:26 (8.0s): Step 3B: AGT_THEME=light agt ps --once (Light Theme Auto-Sync: Rosewood & Gold)
  • 00:26 - 00:31 (5.0s): Step 4: agt fallback -t /tmp/demo-sandbox --step-down orchestrator (Model Quota Rotation)
  • 00:31 - 00:33 (2.0s): Outro Buffer & Clean Prompt Loopback
"""

import os
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

AGT_BIN = "/home/killua/.local/bin/agt"
PROJECT_DIR = "/home/killua/Projects/agent-team"
DEMO_SANDBOX = Path("/tmp/demo-sandbox")
START_TOKEN = Path("/tmp/agt_demo_start")
READY_TOKEN = Path("/tmp/agt_demo_ready")

PROMPT = "\033[01;32mkillua@resolute\033[00m:\033[01;34m~/Projects/agent-team\033[00m$ "
CLEAR_SCREEN = "\033[2J\033[3J\033[H"


def typewriter(text: str, min_delay: float = 0.035, max_delay: float = 0.065) -> None:
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
    extra_env: dict[str, str] | None = None,
) -> None:
    """Run command preserving terminal formatting and ANSI codes."""
    env = os.environ.copy()
    env["COLORTERM"] = "truecolor"
    env["TERM"] = "xterm-256color"
    env["FORCE_COLOR"] = "1"
    if extra_env:
        env.update(extra_env)

    subprocess.run(
        cmd,
        cwd=PROJECT_DIR,
        env=env,
        check=True,
    )


def wait_for_handshake() -> None:
    """Wait for compositor animation settling signal from recorder."""
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.flush()

    if os.environ.get("AGT_DEMO_SYNC") == "1":
        while not START_TOKEN.exists():
            time.sleep(0.01)


def main() -> None:
    if not Path(AGT_BIN).exists():
        sys.stderr.write(f"Error: {AGT_BIN} not found.\n")
        sys.exit(1)

    # Initialize demo sandbox
    shutil.rmtree(DEMO_SANDBOX, ignore_errors=True)
    DEMO_SANDBOX.mkdir(parents=True, exist_ok=True)

    wait_for_handshake()

    # -------------------------------------------------------------
    # Frame 0 & Step 1: Render agt status immediately for hero display
    # -------------------------------------------------------------
    sys.stdout.write(PROMPT + "agt status\n")
    sys.stdout.flush()
    run_command([AGT_BIN, "status"])
    sys.stdout.write("\n" + PROMPT)
    sys.stdout.flush()

    # Signal readiness NOW: Screen is guaranteed to be full of colorful content
    t0 = time.monotonic()
    READY_TOKEN.write_text(f"{t0:.4f}")

    # Hold Step 1 for 5 seconds so viewers can comfortably view mascots & specs
    wait_until(t0, 5.0)

    # -------------------------------------------------------------
    # 00:05 - 00:11 (6.0s): Step 2: agt init -t /tmp/demo-sandbox -y
    # -------------------------------------------------------------
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.write(PROMPT)
    sys.stdout.flush()
    time.sleep(0.1)

    typewriter("agt init -t /tmp/demo-sandbox -y")
    time.sleep(0.12)
    sys.stdout.write("\n")
    sys.stdout.flush()

    run_command([AGT_BIN, "init", "-t", str(DEMO_SANDBOX), "-y"])
    sys.stdout.write("\n" + PROMPT)
    sys.stdout.flush()
    wait_until(t0, 11.0)

    # -------------------------------------------------------------
    # 00:11 - 00:18 (7.0s): Step 3A: agt ps --once (Dark Theme)
    # -------------------------------------------------------------
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.write(PROMPT)
    sys.stdout.flush()
    time.sleep(0.1)

    typewriter('agt ps --once --active "architect,critic"')
    time.sleep(0.12)
    sys.stdout.write("\n")
    sys.stdout.flush()

    run_command(
        [AGT_BIN, "ps", "--once", "--active", "architect,critic"],
        extra_env={"AGT_THEME": "dark"},
    )
    sys.stdout.write("\n" + PROMPT)
    sys.stdout.flush()
    wait_until(t0, 18.0)

    # -------------------------------------------------------------
    # 00:18 - 00:26 (8.0s): Step 3B: Theme Auto-Sync Showcase (Light Theme)
    # -------------------------------------------------------------
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.write(PROMPT)
    sys.stdout.flush()
    time.sleep(0.1)

    typewriter('AGT_THEME=light agt ps --once --active "designer,implementer"')
    time.sleep(0.12)
    sys.stdout.write("\n")
    sys.stdout.flush()

    run_command(
        [AGT_BIN, "ps", "--once", "--active", "designer,implementer"],
        extra_env={"AGT_THEME": "light"},
    )
    sys.stdout.write("\n" + PROMPT)
    sys.stdout.flush()
    wait_until(t0, 26.0)

    # -------------------------------------------------------------
    # 00:26 - 00:31 (5.0s): Step 4: agt fallback Quota Rotation
    # -------------------------------------------------------------
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.write(PROMPT)
    sys.stdout.flush()
    time.sleep(0.1)

    typewriter("agt fallback -t /tmp/demo-sandbox --step-down orchestrator")
    time.sleep(0.12)
    sys.stdout.write("\n")
    sys.stdout.flush()

    run_command(
        [AGT_BIN, "fallback", "-t", str(DEMO_SANDBOX), "--step-down", "orchestrator"],
    )
    sys.stdout.write("\n" + PROMPT)
    sys.stdout.flush()
    wait_until(t0, 31.0)

    # -------------------------------------------------------------
    # 00:31 - 00:33 (2.0s): Outro Buffer
    # -------------------------------------------------------------
    wait_until(t0, 33.0)


if __name__ == "__main__":
    main()
