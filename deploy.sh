#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "  GymClaw - 一键更新部署"
echo "============================================"
echo ""

BRANCH="${1:-main}"
echo "[1/5] 拉取最新代码 (分支: $BRANCH)..."
cd "$PROJECT_DIR"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"
echo "  代码更新完成"

echo "[2/5] 更新 Python 依赖..."
if [ -f "requirements.txt" ]; then
    venv/bin/pip install -q -r requirements.txt
    echo "  Python 依赖已更新"
else
    echo "  [SKIP] requirements.txt 不存在"
fi

echo "[3/5] 构建前端..."
if [ -f "frontend/package.json" ]; then
    cd "$PROJECT_DIR/frontend"
    npm install --production=false
    npm run build
    cd "$PROJECT_DIR"
    echo "  前端构建完成"
else
    echo "  [SKIP] frontend/package.json 不存在"
fi

echo "[4/5] 重启服务..."
if systemctl is-active --quiet ai-backend 2>/dev/null; then
    sudo systemctl restart ai-backend
    echo "  ai-backend 已重启"
else
    echo "  [SKIP] ai-backend 服务未运行"
fi

if systemctl is-active --quiet ai-frontend 2>/dev/null; then
    sudo systemctl restart ai-frontend
    echo "  ai-frontend 已重启"
else
    echo "  [SKIP] ai-frontend 服务未运行"
fi

echo "[5/5] 检查服务状态..."
sleep 3
echo ""
echo "--- Backend ---"
systemctl is-active ai-backend 2>/dev/null && echo "  ✓ 运行中" || echo "  ✗ 未运行"
echo "--- Frontend ---"
systemctl is-active ai-frontend 2>/dev/null && echo "  ✓ 运行中" || echo "  ✗ 未运行"
echo ""

echo "============================================"
echo "  部署完成！"
echo "============================================"
echo ""
echo "  查看日志: tail -f $PROJECT_DIR/logs/*.log"
echo ""
