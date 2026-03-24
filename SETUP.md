# 放生龙虾 — OpenClaw 部署指南

## 1. 工作区配置

把这个项目的文件放进 OpenClaw workspace：

```bash
# 方法一：直接把整个目录作为 workspace（推荐）
# 在 ~/.openclaw/openclaw.json 里配置：
# "agent": { "workspace": "/path/to/wanderClaw" }

# 方法二：软链接
ln -s /path/to/wanderClaw ~/.openclaw/workspace
```

## 2. openclaw.json 配置

```json
{
  "identity": {
    "name": "虾游",
    "emoji": "🦐"
  },
  "agent": {
    "workspace": "/path/to/wanderClaw",
    "model": "anthropic/claude-sonnet-4-6"
  },
  "agents": {
    "defaults": {
      "heartbeat": {
        "every": "30m",
        "activeHours": { "start": "08:00", "end": "23:00" }
      }
    }
  },
  "channels": {
    "feishu": {
      "enabled": true,
      "accounts": {
        "main": {
          "appId": "cli_xxx",
          "appSecret": "xxx",
          "botName": "虾游"
        }
      }
    }
  },
  "tools": {
    "web": {
      "search": {
        "provider": "brave"
      },
      "fetch": {
        "maxChars": 30000
      }
    }
  }
}
```

## 3. Cron 任务注册

```bash
# 深度探索 — 每天 10:00（带30分钟随机抖动）
openclaw cron add \
  --name "虾游深度探索-上午" \
  --cron "0 10 * * *" \
  --session isolated \
  --model "anthropic/claude-haiku-4-5-20251001" \
  --stagger 30m \
  --prompt "$(cat /path/to/wanderClaw/shrimp-wanderer/EXPLORER.md)"

# 深度探索 — 每天 15:00
openclaw cron add \
  --name "虾游深度探索-下午" \
  --cron "0 15 * * *" \
  --session isolated \
  --model "anthropic/claude-haiku-4-5-20251001" \
  --stagger 30m \
  --prompt "$(cat /path/to/wanderClaw/shrimp-wanderer/EXPLORER.md)"

# 轻度扫描 — 每天 12:00 和 20:00
openclaw cron add \
  --name "虾游轻度扫描-中午" \
  --cron "0 12 * * *" \
  --session isolated \
  --model "anthropic/claude-haiku-4-5-20251001" \
  --stagger 60m \
  --prompt "执行一次轻度扫描：只检查核心水域的最新热门内容，5分钟内完成。有重大发现（评分≥8）才推送明信片，否则只归档。"

openclaw cron add \
  --name "虾游轻度扫描-晚上" \
  --cron "0 20 * * *" \
  --session isolated \
  --model "anthropic/claude-haiku-4-5-20251001" \
  --stagger 60m \
  --prompt "执行一次轻度扫描：只检查核心水域的最新热门内容，5分钟内完成。有重大发现（评分≥8）才推送明信片，否则只归档。"

# 周度总结 — 每周日 21:00
openclaw cron add \
  --name "虾游周度总结" \
  --cron "0 21 * * 0" \
  --session isolated \
  --prompt "回顾本周所有探索日记（shrimp-wanderer/exploration-log/），生成一份简短的周报发给阿哲，更新 interest-graph.json 中各方向的权重。"
```

## 4. 查看 cron 任务

```bash
openclaw cron list
```

## 5. 手动触发一次探索（测试用）

```bash
openclaw run --prompt "$(cat /path/to/wanderClaw/shrimp-wanderer/EXPLORER.md)"
```

## 6. 飞书 Bot 权限配置

在飞书开放平台需要的权限：
- `im:message` — 发消息
- `im:message:send_as_bot` — 以 Bot 身份发消息
- `im:resource` — 发文件/图片（可选）

事件订阅：
- `im.message.receive_v1` — 接收用户消息（长连接模式）

## 7. 验证配置

```bash
openclaw doctor
```
