# 🦐 虾游 (WanderClaw)

> 替你逛互联网，把好东西寄回来。

一只有好奇心的 AI 龙虾，每天在互联网深处探险，把发现的知识宝藏写成明信片寄给你。

**OpenClaw Skill** — 安装即用，零代码，零配置。

## 安装

```bash
clawhub install wanderclaw
```

## 它会做什么

1. **装完自动打招呼**，问你对什么感兴趣
2. **冷启动三连探索**（30秒/4分钟/8分钟各出发一次），快速产出前 3 张明信片
3. **每天 4 次定时探索**（9:00 / 12:00 / 15:00 / 20:00），持续发现新内容
4. **明信片推送**到你的聊天窗口——有标题、有观点、有原文链接
5. **兴趣图谱自动演化**——聊天中提到的新兴趣会被捕获，探索方向逐渐个性化

## 要求

- **OpenClaw** 运行中
- **搜索工具**：至少一种（Gemini web_search 免费 / Brave / 或装个 ddg-search skill）
- **推荐模型**：Sonnet 4 或以上

## 项目结构

```
wanderClaw/
├── SKILL.md              # Skill 定义（触发规则、Onboarding、探索流程）
├── references/
│   ├── EXPLORER.md       # 探索引擎六步流程
│   ├── SOUL.md           # 虾游人格
│   ├── postcard-format.md # 明信片格式规范
│   └── sources.yaml      # 三层水域信息源
├── assets/
│   ├── state.json        # 状态模板
│   └── interest-graph.json # 兴趣图谱模板
├── scripts/
│   ├── schedule-cron.sh  # 注册定时探索 + 冷启动 cron
│   ├── cold-start-trigger.sh # 冷启动单次探索触发
│   └── setup.sh          # 首次安装初始化
└── team/                 # 开发文档（BACKLOG / CHANGELOG / DECISIONS）
```

安装后，用户 workspace 会多一个 `wanderclaw/` 目录存放运行数据（明信片、探索日志、兴趣图谱等）。

## 许可

Apache 2.0
