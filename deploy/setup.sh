#!/bin/bash
set -e

PROJECT_DIR="/opt/ai-assistant"
LOG_DIR="$PROJECT_DIR/logs"
DATA_DIR="$PROJECT_DIR/data"
UPLOAD_DIR="$PROJECT_DIR/data/uploads"

echo "============================================"
echo "  GymClaw - 服务器初始化脚本"
echo "  适用于 Ubuntu 22.04 / 24.04"
echo "============================================"
echo ""

if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] 请使用 sudo 运行此脚本"
    exit 1
fi

echo "[1/8] 更新系统包..."
apt update && apt upgrade -y

echo "[2/8] 安装基础依赖..."
apt install -y \
    git curl wget \
    build-essential \
    nginx \
    python3 python3-pip python3-venv \
    nodejs npm

echo "[3/8] 创建项目目录..."
mkdir -p "$PROJECT_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"
mkdir -p "$UPLOAD_DIR"

echo "[4/8] 创建 www-data 用户工作目录..."
user_home=$(eval echo "~www-data")
mkdir -p "$user_home"
chown www-data:www-data "$user_home"

echo "[5/8] 克隆代码（请确认 Gitee 仓库地址）..."
if [ -d "$PROJECT_DIR/.git" ]; then
    echo "  代码已存在，跳过克隆"
else
    read -p "  请输入 Gitee 仓库地址 (例: https://gitee.com/xxx/ai-assistant.git): " REPO_URL
    if [ -z "$REPO_URL" ]; then
        echo "  [WARN] 未输入仓库地址，请稍后手动克隆代码到 $PROJECT_DIR"
        echo "  git clone <your-repo> $PROJECT_DIR"
    else
        git clone "$REPO_URL" "$PROJECT_DIR"
    fi
fi

echo "[6/8] 安装后端 Python 依赖..."
if [ -f "$PROJECT_DIR/requirements.txt" ]; then
    python3 -m venv "$PROJECT_DIR/venv"
    $PROJECT_DIR/venv/bin/pip install --upgrade pip
    $PROJECT_DIR/venv/bin/pip install -r "$PROJECT_DIR/requirements.txt"
    echo "  Python 依赖安装完成"
else
    echo "  [WARN] requirements.txt 不存在，跳过"
fi

echo "[7/8] 构建前端..."
if [ -f "$PROJECT_DIR/frontend/package.json" ]; then
    cd "$PROJECT_DIR/frontend"
    npm install
    npm run build
    cd "$PROJECT_DIR"
    echo "  前端构建完成"
else
    echo "  [WARN] frontend/package.json 不存在，跳过"
fi

echo "[8/8] 配置 Nginx 和 systemd..."
if [ -f "$PROJECT_DIR/deploy/nginx.conf" ]; then
    cp "$PROJECT_DIR/deploy/nginx.conf" /etc/nginx/sites-available/ai-assistant
    ln -sf /etc/nginx/sites-available/ai-assistant /etc/nginx/sites-enabled/ai-assistant
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && echo "  Nginx 配置验证通过" || echo "  [ERROR] Nginx 配置有误"
fi

if [ -f "$PROJECT_DIR/deploy/ai-backend.service" ]; then
    cp "$PROJECT_DIR/deploy/ai-backend.service" /etc/systemd/system/
    cp "$PROJECT_DIR/deploy/ai-frontend.service" /etc/systemd/system/
    systemctl daemon-reload
    echo "  systemd 服务文件已安装"
fi

chown -R www-data:www-data "$PROJECT_DIR"

echo ""
echo "============================================"
echo "  初始化完成！"
echo "============================================"
echo ""
echo "后续步骤："
echo "  1. 编辑 .env 文件："
echo "     sudo -u www-data nano $PROJECT_DIR/.env"
echo ""
echo "  2. 编辑 Nginx 域名："
echo "     sudo nano /etc/nginx/sites-available/ai-assistant"
echo "     将 YOUR_DOMAIN 替换为你的域名"
echo ""
echo "  3. 启动服务："
echo "     sudo systemctl enable ai-backend ai-frontend"
echo "     sudo systemctl start ai-backend ai-frontend"
echo "     sudo systemctl reload nginx"
echo ""
echo "  4. 查看状态："
echo "     sudo systemctl status ai-backend"
echo "     sudo systemctl status ai-frontend"
echo "     sudo tail -f $PROJECT_DIR/logs/*.log"
echo ""
echo "  5. 后续更新代码："
echo "     cd $PROJECT_DIR && bash deploy.sh"
echo ""
