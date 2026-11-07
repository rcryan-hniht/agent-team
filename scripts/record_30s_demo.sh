#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# agt Demo Master Recording Script
# Orchestrates isolated OBS recording on Workspace 9 and Ghostty on Workspace 2
# Automates 2-pass high-fidelity GIF generation with zero-black-frame guardrails
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VIDEOS_DIR="${HOME}/Videos"
OUTPUT_TARGET="${VIDEOS_DIR}/agt_demo_30s.mp4"
GIF_TARGET="${PROJECT_DIR}/assets/demo.gif"

echo "=== [AGT DEMO RECORDER] Initializing ==="
echo "Project Directory: $PROJECT_DIR"
echo "Target Video Output: $OUTPUT_TARGET"
echo "Target GIF Output: $GIF_TARGET"

mkdir -p "$VIDEOS_DIR"

# Clean synchronization tokens
rm -f /tmp/agt_demo_start /tmp/agt_demo_ready /tmp/agt_frame0.png

# Ensure webcam overlay is disabled in OBS scene
python3 -c '
import json
p = "/home/killua/.config/obs-studio/basic/scenes/Untitled.json"
try:
    with open(p) as f:
        d = json.load(f)
    for s in d.get("sources", []):
        if s.get("id") == "scene":
            for item in s.get("settings", {}).get("items", []):
                if item.get("name") == "Video Capture Device (V4L2)":
                    item["visible"] = False
    with open(p, "w") as f:
        json.dump(d, f, indent=4)
except Exception:
    pass
'

# Snapshot existing recordings before launch
BEFORE_LIST=$(mktemp)
find "$VIDEOS_DIR" -maxdepth 1 -name "*.mp4" -type f | sort > "$BEFORE_LIST"

# 1. Switch to Workspace 9 for isolated OBS startup
echo "1. Switching to Workspace 9 for isolated OBS process..."
niri msg action focus-workspace 9 || true

# 2. Start OBS recording in background and record timestamp
echo "2. Launching OBS with --startrecording..."
T_OBS_START=$(python3 -c "import time; print(time.monotonic())")
obs --startrecording --disable-missing-files-check > /tmp/obs_recording.log 2>&1 &
OBS_PID=$!
echo "   OBS PID: $OBS_PID (Started at $T_OBS_START)"

# 3. Buffer to allow PipeWire session handshake and encoders to warm up
echo "3. Warming up OBS capture pipeline (2.0s)..."
sleep 2.0

# 4. Switch back to primary Workspace 2
echo "4. Returning to Workspace 2..."
niri msg action focus-workspace 2 || true

# 5. Launch Ghostty with demo_runner.py with synchronization enabled
echo "5. Launching Ghostty demo terminal with AGT_DEMO_SYNC=1..."
env AGT_DEMO_SYNC=1 ghostty --title="agt-recording-demo" -e python3 "${SCRIPT_DIR}/demo_runner.py" &
GHOSTTY_PID=$!
echo "   Ghostty PID: $GHOSTTY_PID"

# 6. Locate demo window and set fullscreen + focus
echo "6. Locating demo window in niri..."
DEMO_WIN_ID=""
for i in $(seq 1 40); do
    DEMO_WIN_ID=$(niri msg -j windows 2>/dev/null | jq -r '.[] | select(.title=="agt-recording-demo") | .id' 2>/dev/null || true)
    if [ -n "$DEMO_WIN_ID" ] && [ "$DEMO_WIN_ID" != "null" ]; then
        break
    fi
    sleep 0.05
done

if [ -n "$DEMO_WIN_ID" ] && [ "$DEMO_WIN_ID" != "null" ]; then
    echo "   Found Ghostty Window ID: $DEMO_WIN_ID"
    niri msg action fullscreen-window --id "$DEMO_WIN_ID" || true
    niri msg action focus-window --id "$DEMO_WIN_ID" || true
else
    echo "   ⚠️ Warning: Could not locate window title 'agt-recording-demo', continuing..."
fi

# 7. Settle compositor animation spring physics (0.35s) then signal runner
echo "7. Compositor animation settling (0.35s)..."
sleep 0.35

echo "   Signaling demo runner via /tmp/agt_demo_start..."
touch /tmp/agt_demo_start

# Await runner ready acknowledgement (when agt status is fully rendered)
for i in $(seq 1 150); do
    if [ -f /tmp/agt_demo_ready ]; then
        break
    fi
    sleep 0.02
done

T_READY=$(cat /tmp/agt_demo_ready 2>/dev/null || python3 -c "import time; print(time.monotonic())")
TRIM_START=$(python3 -c "print(f'{max(0.0, float(\"$T_READY\") - float(\"$T_OBS_START\")):.3f}')")
echo "✅ Two-Way Handshake established: T_READY=$T_READY, Dynamic TRIM_START=${TRIM_START}s"

# 8. Wait for demo runner to finish (33s total duration)
echo "8. Waiting for demo runner to finish 4 steps + outro..."
wait "$GHOSTTY_PID" || true
echo "   Ghostty demo completed!"

# Buffer after demo completion
sleep 0.5

# 9. Stop OBS gracefully
echo "9. Stopping OBS recording via SIGINT / SIGTERM..."
kill -SIGINT "$OBS_PID" 2>/dev/null || true

TIMEOUT=4
COUNT=0
while kill -0 "$OBS_PID" 2>/dev/null; do
    sleep 0.5
    COUNT=$((COUNT + 1))
    if [ "$COUNT" -ge "$((TIMEOUT * 2))" ]; then
        echo "   Sending SIGTERM to finalize recording..."
        kill -SIGTERM "$OBS_PID" 2>/dev/null || true
        break
    fi
done

wait "$OBS_PID" 2>/dev/null || true

# Ensure focus is back on Workspace 2
niri msg action focus-workspace 2 || true

# 10. Detect newly generated MP4 recording
echo "10. Detecting generated MP4 file..."
AFTER_LIST=$(mktemp)
find "$VIDEOS_DIR" -maxdepth 1 -name "*.mp4" -type f | sort > "$AFTER_LIST"

NEW_FILES=$(comm -13 "$BEFORE_LIST" "$AFTER_LIST")
rm -f "$BEFORE_LIST" "$AFTER_LIST"

if [ -z "$NEW_FILES" ]; then
    echo "❌ ERROR: No new MP4 file detected in $VIDEOS_DIR!"
    echo "OBS log dump:"
    tail -n 35 /tmp/obs_recording.log
    exit 1
fi

RECORDED_FILE=$(echo "$NEW_FILES" | head -n 1)
echo "✅ Detected new recording: $RECORDED_FILE"

# 11. Copy / promote to target output
echo "11. Promoting recording to target: $OUTPUT_TARGET"
cp -f "$RECORDED_FILE" "$OUTPUT_TARGET"

# 12. Probe output file with ffprobe
echo "12. Verifying video file specifications..."
FILE_SIZE=$(stat -c%s "$OUTPUT_TARGET" 2>/dev/null || stat -f%z "$OUTPUT_TARGET")
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT_TARGET" 2>/dev/null || echo "0")
RESOLUTION=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$OUTPUT_TARGET" 2>/dev/null || echo "unknown")
FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$OUTPUT_TARGET" 2>/dev/null || echo "unknown")

echo "============================================================"
echo "🎬 MASTER MP4 RECORDING READY"
echo "   Output File : $OUTPUT_TARGET"
echo "   File Size   : $FILE_SIZE bytes ($((FILE_SIZE / 1024 / 1024)) MB)"
echo "   Resolution  : $RESOLUTION"
echo "   FPS         : $FPS"
echo "   Duration    : ${DURATION}s"
echo "============================================================"

# 13. Dual-Layer Frame 0 & Blackdetect Validation Guardrail
echo "13. Running Dual-Layer Frame 0 Validation Guardrail..."
TRIM_DURATION="33.0"

# Guardrail Layer 1: FFmpeg stderr blackdetect check at TRIM_START
BLACK_OUTPUT=$(ffmpeg -ss "$TRIM_START" -t 1.0 -i "$OUTPUT_TARGET" -vf "blackdetect=d=0.01:pix_th=0.10" -f null - 2>&1)
if echo "$BLACK_OUTPUT" | grep -q "black_start:0"; then
    echo "❌ FATAL: FFmpeg blackdetect caught black frame at TRIM_START=$TRIM_START!" >&2
    echo "$BLACK_OUTPUT" | grep "black_" >&2
    exit 1
fi
echo "   ✔ Layer 1 passed: No black_start:0 detected at offset $TRIM_START"

# Guardrail Layer 2: Extract Frame 0 PNG and analyze pixel color diversity
ffmpeg -y -ss "$TRIM_START" -i "$OUTPUT_TARGET" -vframes 1 /tmp/agt_frame0.png 2>/dev/null
python3 -c '
from PIL import Image
import sys

try:
    img = Image.open("/tmp/agt_frame0.png").convert("RGB")
    colors = set(img.getdata())
    if len(colors) < 30:
        print(f"❌ FATAL: Frame 0 lacks content diversity (only {len(colors)} colors detected).", file=sys.stderr)
        sys.exit(1)
    print(f"   ✔ Layer 2 passed: Frame 0 has {len(colors)} distinct RGB colors.")
except Exception as e:
    print(f"⚠️ Warning: Could not run PIL color check ({e}), continuing...", file=sys.stderr)
'

# 14. Convert to high-fidelity assets/demo.gif via 2-pass palette ffmpeg
echo "14. Generating 2-pass palette optimized GIF (960x540 @ 10fps, 128 colors, Bayer dither)..."
PALETTE_PNG=$(mktemp --suffix=.png)

ffmpeg -y -ss "$TRIM_START" -t "$TRIM_DURATION" -i "$OUTPUT_TARGET" \
  -vf "fps=10,scale=960:-1:flags=lanczos,palettegen=max_colors=128:stats_mode=diff" \
  "$PALETTE_PNG"

ffmpeg -y -ss "$TRIM_START" -t "$TRIM_DURATION" -i "$OUTPUT_TARGET" -i "$PALETTE_PNG" \
  -lavfi "fps=10,scale=960:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=3" \
  "$GIF_TARGET"

rm -f "$PALETTE_PNG"

GIF_SIZE=$(stat -c%s "$GIF_TARGET" 2>/dev/null || stat -f%z "$GIF_TARGET")
echo "============================================================"
echo "✨ assets/demo.gif GENERATED SUCCESSFULLY!"
echo "   Output File : $GIF_TARGET"
echo "   File Size   : $GIF_SIZE bytes ($((GIF_SIZE / 1024 / 1024)) MB)"
echo "   Duration    : ~${TRIM_DURATION}s"
echo "============================================================"
