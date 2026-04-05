#!/bin/bash
# ============================================================
# GymClaw 停止脚本 (Mac / Linux)
# ============================================================

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

PID_DIR="$PROJECT_ROOT/.pids"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"

echo "Stopping GymClaw..."

stop_process() {
    local pid_file="$1"
    local name="$2"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo "  $name stopped (PID: $pid)"
        else
            echo "  $name already stopped"
        fi
        rm -f "$pid_file"
    else
        echo "  $name: no PID file"
    fi
}

stop_process "$BACKEND_PID_FILE" "Backend"
stop_process "$FRONTEND_PID_FILE" "Frontend"

echo "Done."
