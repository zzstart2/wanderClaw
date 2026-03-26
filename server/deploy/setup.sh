#!/bin/bash
set -e

echo "=== WanderClaw 部署脚本 ==="

# 1. 创建用户数据目录
mkdir -p /root/wanderClaw/users
echo "✅ 用户数据目录已创建"

# 2. 安装 systemd service
cp "$(dirname "$0")/wanderclaw.service" /etc/systemd/system/
systemctl daemon-reload
echo "✅ systemd service 已安装"

# 3. 启动服务
systemctl enable wanderclaw
systemctl start wanderclaw
echo "✅ 服务已启动"

# 4. 检查状态
sleep 2
if systemctl is-active --quiet wanderclaw; then
    echo "✅ WanderClaw 服务运行中 (端口 8080)"
    echo ""
    echo "查看日志: journalctl -u wanderclaw -f"
    echo "重启服务: systemctl restart wanderclaw"
    echo "停止服务: systemctl stop wanderclaw"
else
    echo "❌ 服务启动失败，查看日志:"
    journalctl -u wanderclaw -n 20
    exit 1
fi
