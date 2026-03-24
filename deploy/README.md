# WanderClaw 部署指南

## 快速部署

```bash
cd projects/wanderClaw/deploy
chmod +x setup.sh
sudo ./setup.sh
```

## 管理命令

```bash
# 查看状态
systemctl status wanderclaw

# 查看日志（实时）
journalctl -u wanderclaw -f

# 重启
systemctl restart wanderclaw

# 停止
systemctl stop wanderclaw
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| PORT | 8080 | HTTP 监听端口 |
| WANDERCLAW_USERS_BASE | /root/wanderClaw/users | 用户 workspace 根目录 |
| OPENCLAW_CONFIG | /root/.openclaw/openclaw.json | OpenClaw 配置文件路径 |

## 端口

服务监听 0.0.0.0:8080，确保防火墙允许外部访问：

```bash
# 如果用 iptables
iptables -A INPUT -p tcp --dport 8080 -j ACCEPT

# 如果用 firewalld
firewall-cmd --add-port=8080/tcp --permanent
firewall-cmd --reload

# 如果用阿里云安全组
# 在阿里云控制台添加入方向规则：TCP 8080
```
