#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# agt Demo Master Recording Script
# Orchestrates isolated OBS recording on Workspace 9 and Ghostty on Workspace 2
# Automates 2-pass high-fidelity GIF generation to assets/demo.gif
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VIDEOS_DIR="${HOME}/Videos"
OUTPUT_TARGET="${VIDEOS_DIR}/agt_demo_30s.mp4"

echo "=== [AGT DEMO RECORDER] Initializing ==="
echo "Project Directory: $PROJECT_DIR"
echo "Target Video Output: $OUTPUT_TARGET"

mkdir -p "$VIDEOS_DIR"

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

# 2. Start OBS recording in background
echo "2. Launching OBS with --startrecording..."
obs --startrecording --disable-missing-files-check > /tmp/obs_recording.log 2>&1 &
OBS_PID=$!
echo "   OBS PID: $OBS_PID"

# 3. Buffer to allow PipeWire session handshake and encoders to warm up
echo "3. Warming up OBS capture pipeline (2.0s)..."
sleep 2.0

# 4. Switch back to primary Workspace 2
echo "4. Returning to Workspace 2..."
niri msg action focus-workspace 2 || true

# 5. Launch Ghostty with demo_runner.py
echo "5. Launching Ghostty demo terminal..."
ghostty --title="agt-recording-demo" -e python3 "${SCRIPT_DIR}/demo_runner.py" &
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
    sleep 0.1
done

if [ -n "$DEMO_WIN_ID" ] && [ "$DEMO_WIN_ID" != "null" ]; then
    echo "   Found Ghostty Window ID: $DEMO_WIN_ID"
    niri msg action fullscreen-window --id "$DEMO_WIN_ID" || true
    niri msg action focus-window --id "$DEMO_WIN_ID" || true
else
    echo "   ⚠️ Warning: Could not locate window title 'agt-recording-demo', continuing..."
fi

# 7. Wait for demo runner to finish (47s total duration)
echo "7. Waiting for demo runner to finish all segments..."
wait "$GHOSTTY_PID" || true
echo "   Ghostty demo completed!"

# Buffer after demo completion
sleep 0.5

# 8. Stop OBS gracefully
echo "8. Stopping OBS recording via SIGINT / SIGTERM..."
kill -SIGINT "$OBS_PID" 2>/dev/null || true

TIMEOUT=2
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

# 9. Detect newly generated MP4 recording
echo "9. Detecting generated MP4 file..."
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

# 10. Copy / rename to target output
echo "10. Promoting recording to target: $OUTPUT_TARGET"
cp -f "$RECORDED_FILE" "$OUTPUT_TARGET"

# 11. Probe output file with ffprobe
echo "11. Verifying video file specifications..."
FILE_SIZE=$(stat -c%s "$OUTPUT_TARGET" 2>/dev/null || stat -f%z "$OUTPUT_TARGET")
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$OUTPUT_TARGET" 2>/dev/null || echo "0")
RESOLUTION=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$OUTPUT_TARGET" 2>/dev/null || echo "unknown")
FPS=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of default=noprint_wrappers=1:nokey=1 "$OUTPUT_TARGET" 2>/dev/null || echo "unknown")

echo "============================================================"
echo "🎬 DEMO RECORDING FINISHED SUCCESSFULLY!"
echo "   Output File : $OUTPUT_TARGET"
echo "   File Size   : $FILE_SIZE bytes ($((FILE_SIZE / 1024 / 1024)) MB)"
echo "   Resolution  : $RESOLUTION"
echo "   FPS         : $FPS"
echo "   Duration    : ${DURATION}s"
echo "============================================================"

# 12. Convert to high-fidelity assets/demo.gif via 2-pass palette ffmpeg
# Cut out initial 4.0s (startup/workspace switch) so ONLY fullscreen Ghostty terminal is shown
echo "12. Converting to assets/demo.gif (trimming startup to isolate Ghostty terminal)..."
TRIM_START="00:00:04.0"
TRIM_DURATION="47.0"

PALETTE_PNG=$(mktemp --suffix=.png)
ffmpeg -y -ss "$TRIM_START" -t "$TRIM_DURATION" -i "$OUTPUT_TARGET" -vf "fps=10,scale=960:-1:flags=lanczos,palettegen=max_colors=96:stats_mode=diff" "$PALETTE_PNG"
ffmpeg -y -ss "$TRIM_START" -t "$TRIM_DURATION" -i "$OUTPUT_TARGET" -i "$PALETTE_PNG" -lavfi "fps=10,scale=960:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=3" "${PROJECT_DIR}/assets/demo.gif"
rm -f "$PALETTE_PNG"

GIF_SIZE=$(stat -c%s "${PROJECT_DIR}/assets/demo.gif" 2>/dev/null || stat -f%z "${PROJECT_DIR}/assets/demo.gif")
echo "✅ assets/demo.gif generated: $GIF_SIZE bytes ($((GIF_SIZE / 1024 / 1024)) MB)"
