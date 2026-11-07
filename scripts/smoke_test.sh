#!/usr/bin/env bash
set -euo pipefail

echo "=== [SMOKE TEST] OBS PipeWire Recording Test ==="

VIDEOS_DIR="${HOME}/Videos"
mkdir -p "$VIDEOS_DIR"

# Snapshot existing files before recording
BEFORE_LIST=$(mktemp)
find "$VIDEOS_DIR" -maxdepth 1 -name "*.mp4" -type f | sort > "$BEFORE_LIST"

echo "1. Switching to Workspace 9 for OBS launch..."
niri msg action focus-workspace 9 || true

echo "2. Launching OBS Studio with --startrecording..."
obs --startrecording --disable-missing-files-check > /tmp/obs_smoke_test.log 2>&1 &
OBS_PID=$!
echo "   OBS PID: $OBS_PID"

echo "3. Recording for 6 seconds to ensure PipeWire handshake is fully established..."
sleep 6.0

echo "4. Stopping OBS gracefully with SIGINT..."
kill -SIGINT "$OBS_PID" 2>/dev/null || true

# Wait for OBS process to exit cleanly
TIMEOUT=10
COUNT=0
while kill -0 "$OBS_PID" 2>/dev/null; do
    sleep 0.5
    COUNT=$((COUNT + 1))
    if [ "$COUNT" -ge "$((TIMEOUT * 2))" ]; then
        echo "   OBS did not exit within timeout, killing..."
        kill -9 "$OBS_PID" 2>/dev/null || true
        break
    fi
done

# Return focus to Workspace 2
niri msg action focus-workspace 2 || true

echo "5. Detecting generated MP4 file..."
AFTER_LIST=$(mktemp)
find "$VIDEOS_DIR" -maxdepth 1 -name "*.mp4" -type f | sort > "$AFTER_LIST"

NEW_FILES=$(comm -13 "$BEFORE_LIST" "$AFTER_LIST")
rm -f "$BEFORE_LIST" "$AFTER_LIST"

if [ -z "$NEW_FILES" ]; then
    echo "❌ ERROR: No new MP4 file detected in $VIDEOS_DIR!"
    echo "OBS log dump:"
    tail -n 30 /tmp/obs_smoke_test.log
    exit 1
fi

RECORDED_FILE=$(echo "$NEW_FILES" | head -n 1)
echo "✅ Detected new recording: $RECORDED_FILE"

FILE_SIZE=$(stat -c%s "$RECORDED_FILE" 2>/dev/null || stat -f%z "$RECORDED_FILE")
echo "   File Size: $FILE_SIZE bytes"

if [ "$FILE_SIZE" -lt 10000 ]; then
    echo "❌ ERROR: File size too small ($FILE_SIZE bytes), recording likely failed!"
    exit 1
fi

echo "6. Probing video stream with ffprobe..."
DURATION=$(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$RECORDED_FILE" 2>/dev/null || echo "0")
RESOLUTION=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$RECORDED_FILE" 2>/dev/null || echo "unknown")

echo "   Duration: ${DURATION}s"
echo "   Resolution: ${RESOLUTION}"

# Clean up smoke test file
echo "7. Cleaning up test recording..."
rm -f "$RECORDED_FILE"

echo "=== [SMOKE TEST] OBS & PipeWire Portal recording test PASSED! ==="
