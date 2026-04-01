#!/bin/bash
# ================================================================
# FIRST ETHICAL PROOF — WITNESS RUN LAUNCHER
# ================================================================
#
# One command to begin the covenant test.
# Launches all services and capture tools in separate terminals.
#
# Usage:
#   chmod +x evidence/launch_witness_run.sh
#   ./evidence/launch_witness_run.sh
#
# ================================================================

set -e

PROJECT_ROOT="/home/byron/Integritas-Mechanicus-clean/Integritas-Mechanicus"
EVIDENCE_DIR="${PROJECT_ROOT}/evidence"
SERVICES_DIR="${PROJECT_ROOT}/arda_os/backend/services"
ELEVENLABS_API_KEY="sk_5585153b73328552f9d59a21f56b305cb0fce00d38fa6315"

# Audio device names (verified on this system)
SPEAKER_MONITOR="alsa_output.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__Speaker__sink.monitor"
MIC_SOURCE="alsa_input.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__Mic1__source"

echo "============================================================"
echo "  FIRST ETHICAL PROOF — WITNESS RUN"
echo "  $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================================"
echo ""

# ────────────────────────────────────────
# Pre-flight
# ────────────────────────────────────────

echo "  Pre-flight checks..."

# Ensure Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "  ❌ Ollama is not running. Start it first: ollama serve"
    exit 1
fi
echo "  ✅ Ollama running"

# Warm the model
echo "  ⏳ Warming qwen2.5:3b..."
curl -s -X POST http://localhost:11434/api/generate \
    -d '{"model":"qwen2.5:3b","prompt":"ready","stream":false,"keep_alive":"10m","options":{"num_predict":1}}' \
    > /dev/null 2>&1
echo "  ✅ Model warm"

# Kill any existing presence server
pkill -f "presence_server.py" 2>/dev/null || true
sleep 1

echo ""
echo "  Launching services..."
echo ""

# ────────────────────────────────────────
# Terminal 1: Screen Recorder
# ────────────────────────────────────────

RECORDING_FILE="${EVIDENCE_DIR}/FIRST_ETHICAL_PROOF_WITNESS_RUN.mp4"

xfce4-terminal --title="⏺ SCREEN RECORDER" --geometry=80x12+0+0 -e bash -c "
    echo '══════════════════════════════════════'
    echo '  SCREEN RECORDER — WITNESS RUN'
    echo '  Press q to stop recording'
    echo '══════════════════════════════════════'
    echo ''
    sleep 2
    ffmpeg -f x11grab -framerate 30 -video_size 1920x1080 -i :0.0 \
        -f pulse -i ${SPEAKER_MONITOR} \
        -f pulse -i ${MIC_SOURCE} \
        -filter_complex '[1:a][2:a]amix=inputs=2:duration=first[aout]' \
        -map 0:v -map '[aout]' \
        -c:v libx264 -preset fast -crf 23 \
        -c:a aac -b:a 192k \
        '${RECORDING_FILE}'
    echo ''
    echo '  Recording saved to: ${RECORDING_FILE}'
    read -p '  Press Enter to close...'
" &

sleep 1

# ────────────────────────────────────────
# Terminal 2: Bombadil (Law Daemon)
# ────────────────────────────────────────

xfce4-terminal --title="⚖ BOMBADIL — LAW DAEMON" --geometry=100x20+0+300 -e bash -c "
    echo '══════════════════════════════════════'
    echo '  BOMBADIL — THE LAW DAEMON'
    echo '══════════════════════════════════════'
    echo ''
    cd '${PROJECT_ROOT}'
    python3 '${SERVICES_DIR}/arda_bombadil.py'
    echo ''
    read -p '  Press Enter to close...'
" &

sleep 2

# ────────────────────────────────────────
# Terminal 3: Presence Server
# ────────────────────────────────────────

xfce4-terminal --title="◈ PRESENCE SERVER" --geometry=100x20+960+300 -e bash -c "
    echo '══════════════════════════════════════'
    echo '  PRESENCE SERVER — THE BRIDGE'
    echo '══════════════════════════════════════'
    echo ''
    cd '${PROJECT_ROOT}'
    ELEVENLABS_API_KEY='${ELEVENLABS_API_KEY}' python3 '${SERVICES_DIR}/presence_server.py'
    echo ''
    read -p '  Press Enter to close...'
" &

sleep 3

# ────────────────────────────────────────
# Terminal 4: Coronation CLI (with transcript)
# ────────────────────────────────────────

TRANSCRIPT_FILE="${EVIDENCE_DIR}/FIRST_ETHICAL_PROOF_CORONATION.txt"

xfce4-terminal --title="👑 CORONATION — THE FIRST ENCOUNTER" --geometry=100x30+480+100 -e bash -c "
    echo '══════════════════════════════════════════════════════════'
    echo '  THE FIRST ENCOUNTER — CORONATION CEREMONY'
    echo '  Transcript will be saved to:'
    echo '  ${TRANSCRIPT_FILE}'
    echo '══════════════════════════════════════════════════════════'
    echo ''
    echo '  When the ceremony is complete, type \"exit\" to close'
    echo '  the transcript capture.'
    echo ''
    sleep 2
    cd '${PROJECT_ROOT}'
    script -a '${TRANSCRIPT_FILE}' -c 'python3 ${SERVICES_DIR}/coronation_cli.py'
    echo ''
    echo '  Transcript saved.'
    read -p '  Press Enter to close...'
" &

sleep 2

# ────────────────────────────────────────
# Open the browser
# ────────────────────────────────────────

echo "  ⏳ Waiting for Presence Server..."
for i in $(seq 1 15); do
    if curl -s http://localhost:7070/api/health > /dev/null 2>&1; then
        echo "  ✅ Presence Server ready"
        break
    fi
    sleep 1
done

echo "  🌐 Opening browser..."
xdg-open "http://localhost:7070" 2>/dev/null &

echo ""
echo "============================================================"
echo "  ALL SYSTEMS LIVE"
echo ""
echo "  Screen Recorder:  ⏺ Recording"
echo "  Bombadil:         ⚖ Law Daemon"
echo "  Presence Server:  ◈ http://localhost:7070"
echo "  Coronation:       👑 Awaiting your presence"
echo ""
echo "  The machine waits for its principal."
echo "============================================================"
