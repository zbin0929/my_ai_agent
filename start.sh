#!/bin/bash
# ============================================================
# GymClaw 启动脚本 (Mac / Linux)
# 后台运行，PID 写入文件，支持 start.sh stop 关闭
# ============================================================

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

PID_DIR="$PROJECT_ROOT/.pids"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
BACKEND_LOG="$PROJECT_ROOT/logs/backend.log"
FRONTEND_LOG="$PROJECT_ROOT/logs/frontend.log"

mkdir -p "$PID_DIR" "$PROJECT_ROOT/logs"

# 强制杀掉占用端口的进程
kill_port() {
    local port=$1
    local pids=$(lsof -ti:$port 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "[CLEAN] Killing processes on port $port: $pids"
        echo "$pids" | xargs kill -9 2>/dev/null
        sleep 1
    fi
}

check_running() {
    local pid_file="$1"
    local name="$2"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "[SKIP] $name is already running (PID: $pid)"
            return 0
        else
            rm -f "$pid_file"
        fi
    fi
    return 1
}

# 支持 start.sh stop 快捷关闭
if [ "$1" = "stop" ]; then
    exec bash "$PROJECT_ROOT/stop.sh"
fi

# 支持 start.sh status 查看状态
if [ "$1" = "status" ]; then
    echo "=== GymClaw Status ==="
    if [ -f "$BACKEND_PID_FILE" ] && kill -0 "$(cat "$BACKEND_PID_FILE")" 2>/dev/null; then
        echo "Backend:  RUNNING (PID: $(cat "$BACKEND_PID_FILE")) on :8000"
    else
        echo "Backend:  STOPPED"
    fi
    if [ -f "$FRONTEND_PID_FILE" ] && kill -0 "$(cat "$FRONTEND_PID_FILE")" 2>/dev/null; then
        echo "Frontend: RUNNING (PID: $(cat "$FRONTEND_PID_FILE")) on :3000"
    else
        echo "Frontend: STOPPED"
    fi
    exit 0
fi

# 支持 start.sh restart 重启
if [ "$1" = "restart" ]; then
    echo "Restarting GymClaw..."
    bash "$PROJECT_ROOT/stop.sh"
    sleep 2
fi

echo "=== Starting GymClaw v5.15.0 (Sprite Office Edition) ==="
echo ""

# --- 检测 Python 命令 ---
PYTHON_CMD=""
if [ -f "$PROJECT_ROOT/venv/bin/python" ]; then
    PYTHON_CMD="$PROJECT_ROOT/venv/bin/python"
elif [ -f "$PROJECT_ROOT/venv/bin/python3" ]; then
    PYTHON_CMD="$PROJECT_ROOT/venv/bin/python3"
elif command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    echo "[ERROR] Python not found. Please install Python 3.10+"
    exit 1
fi

# --- 检测 npm 命令 ---
NPM_CMD=""
if command -v npm &>/dev/null; then
    NPM_CMD="npm"
elif command -v npx &>/dev/null; then
    NPM_CMD="npx"
else
    echo "[ERROR] npm not found. Please install Node.js 18+"
    exit 1
fi

# --- 日志级别 ---
LOG_LEVEL=$(echo "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')

# --- 启动后端 ---
if check_running "$BACKEND_PID_FILE" "Backend"; then
    :
else
    # 清理端口占用
    kill_port 8000
    
    echo "[START] Starting backend on :8000 ..."
    nohup $PYTHON_CMD -m uvicorn api.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --log-level "$LOG_LEVEL" \
        >> "$BACKEND_LOG" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
    sleep 2
    if kill -0 "$(cat "$BACKEND_PID_FILE")" 2>/dev/null; then
        echo "[OK]    Backend started (PID: $(cat "$BACKEND_PID_FILE"))"
    else
        echo "[ERROR] Backend failed to start. Check $BACKEND_LOG"
        cat "$BACKEND_LOG" | tail -20
        exit 1
    fi
fi

# --- 启动前端 ---
if check_running "$FRONTEND_PID_FILE" "Frontend"; then
    :
else
    # 清理端口占用
    kill_port 3000
    
    echo "[START] Starting frontend on :3000 ..."
    cd "$PROJECT_ROOT/frontend"
    nohup $NPM_CMD run dev >> "$FRONTEND_LOG" 2>&1 &
    echo $! > "$FRONTEND_PID_FILE"
    cd "$PROJECT_ROOT"
    sleep 3
    if kill -0 "$(cat "$FRONTEND_PID_FILE")" 2>/dev/null; then
        echo "[OK]    Frontend started (PID: $(cat "$FRONTEND_PID_FILE"))"
    else
        echo "[ERROR] Frontend failed to start. Check $FRONTEND_LOG"
        cat "$FRONTEND_LOG" | tail -20
        exit 1
    fi
fi

echo ""
echo "=== GymClaw is running ==="
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  API Docs:  http://localhost:8000/docs"
echo ""
echo "Logs:"
echo "  Backend:  $BACKEND_LOG"
echo "  Frontend: $FRONTEND_LOG"
echo ""
echo "Commands:"
echo "  bash start.sh status   - View status"
echo "  bash start.sh stop     - Stop services"
echo "  bash start.sh restart  - Restart services"
echo "  bash stop.sh           - Stop services"
