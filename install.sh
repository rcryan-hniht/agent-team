#!/usr/bin/env bash
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

REPO_URL="https://github.com/rcryan-hniht/agent-team.git"
RAW_URL="https://raw.githubusercontent.com/rcryan-hniht/agent-team/main/agent_team.py"
INSTALL_DIR="${AGT_INSTALL_DIR:-$HOME/Projects/agent-team}"
BIN_DIR="${AGT_BIN_DIR:-$HOME/.local/bin}"

# 1. Python 3.10+ Semantic Version Gate
if ! command -v python3 >/dev/null 2>&1; then
  echo -e "${RED}✘ Error:${NC} Python 3 is not installed or not in PATH." >&2
  echo "Please install Python 3.10+ (e.g. 'sudo apt install python3' or 'brew install python3') and re-run." >&2
  exit 1
fi

if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
  PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
  echo -e "${RED}✘ Error:${NC} Python 3.10+ is required (found Python $PY_VER)." >&2
  exit 1
fi

mkdir -p "$BIN_DIR"

# 2. Local Repo Clone / Update or Atomic Remote Download
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
  TMP_FILE="$(mktemp -t agt_download.XXXXXX)"
  trap 'rm -f "$TMP_FILE"' EXIT
  if ! curl -fsSL "$RAW_URL" -o "$TMP_FILE"; then
    echo -e "${RED}✘ Error:${NC} Failed to download agent_team.py from GitHub. Please check your internet connection." >&2
    exit 1
  fi

  # Non-empty and Shebang validation
  if [ ! -s "$TMP_FILE" ] || ! head -n 1 "$TMP_FILE" | grep -q "^#\!.*python"; then
    echo -e "${RED}✘ Error:${NC} Downloaded file is empty or corrupted." >&2
    exit 1
  fi
  mv "$TMP_FILE" "$BIN_DIR/agt"
  chmod +x "$BIN_DIR/agt"
  trap - EXIT
fi

# 3. Post-install Smoke Test
if ! "$BIN_DIR/agt" --help >/dev/null 2>&1; then
  echo -e "${RED}✘ Error:${NC} Installed binary failed self-test execution." >&2
  exit 1
fi

echo -e "${GREEN}✔ Installed 'agt' to ${BOLD}$BIN_DIR/agt${NC}"

# 4. Shell-Aware PATH Guidance
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
  SHELL_NAME=$(basename "${SHELL:-bash}")
  echo -e "${BLUE}ℹ Add $BIN_DIR to your PATH:${NC}"
  case "$SHELL_NAME" in
    zsh)
      echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc"
      ;;
    fish)
      echo "  fish_add_path ~/.local/bin"
      ;;
    *)
      echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc"
      ;;
  esac
fi

echo -e "\n${BOLD}Ready!${NC} Run ${GREEN}agt${NC} (English) or ${GREEN}agt --lang vi${NC} (Tiếng Việt) to get started."
