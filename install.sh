#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/rcryan-hniht/agent-team.git"
RAW_URL="https://raw.githubusercontent.com/rcryan-hniht/agent-team/main/agent_team.py"
INSTALL_DIR="${AGT_INSTALL_DIR:-$HOME/Projects/agent-team}"
BIN_DIR="${AGT_BIN_DIR:-$HOME/.local/bin}"

mkdir -p "$BIN_DIR"

if command -v git >/dev/null 2>&1; then
  mkdir -p "$(dirname "$INSTALL_DIR")"
  if [ -d "$INSTALL_DIR/.git" ]; then
    git -C "$INSTALL_DIR" pull --ff-only origin main >/dev/null 2>&1 || true
  elif [ ! -d "$INSTALL_DIR" ]; then
    git clone --depth 1 "$REPO_URL" "$INSTALL_DIR" >/dev/null 2>&1 || true
  fi
fi

if [ -f "$INSTALL_DIR/agent_team.py" ]; then
  chmod +x "$INSTALL_DIR/agent_team.py"
  ln -sf "$INSTALL_DIR/agent_team.py" "$BIN_DIR/agt"
else
  curl -fsSL "$RAW_URL" -o "$BIN_DIR/agt"
  chmod +x "$BIN_DIR/agt"
fi

echo "✔ Installed 'agt' to $BIN_DIR/agt"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  echo "ℹ Add $BIN_DIR to your PATH: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
echo "Run 'agt' (English) or 'agt --lang vi' (Tiếng Việt) to get started."
