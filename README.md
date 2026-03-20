# 🦐 放生龙虾

> 一只有好奇心的 AI，替你去互联网深处探险，把发现的知识宝藏寄回给你。

基于 OpenClaw 框架，零代码实现的 AI 知识探索 Agent。

---

## 项目结构

```
wanderClaw/
├── SOUL.md              # 虾游的灵魂（人格配置）
├── USER.md              # 阿哲的信息
├── HEARTBEAT.md         # 用户主动对话时的响应指南
│
└── shrimp-wanderer/
    ├── EXPLORER.md          # 探索引擎执行指南（cron 触发时运行）
    ├── sources.yaml         # 三层水域信息源注册表
    ├── interest-graph.json  # 兴趣图谱（自动维护）
    ├── state.json           # 运行状态（明信片计数、探索历史等）
    │
    ├── postcards/           # 明信片归档（markdown）
    ├── exploration-log/     # 每日探索日记
    └── knowledge-base/      # 按主题分类知识库
        ├── ai/
        ├── philosophy/
        ├── investment/
        └── serendipity/     # 意外发现
```

---

## OpenClaw 配置说明

### 工作区文件
OpenClaw 的 workspace 读取这些文件：
- `SOUL.md` → 人格核心，每次 session 首先注入
- `HEARTBEAT.md` → 每30分钟执行的检查清单
- `USER.md` → 用户信息
- `MEMORY.md` → 长期记忆（由 agent 自动维护）

### Cron 任务
通过 `openclaw cron add` 注册，使用 isolated session + 更便宜的模型：
- 深度探索：每天 10:00 / 15:00（±30分钟抖动）
- 轻度扫描：每天 12:00 / 20:00
- 周度总结：每周日 21:00

详细配置见 `SETUP.md`。

### 工具依赖（OpenClaw 内置）
- `web_search`：互联网搜索（Brave/Gemini/Perplexity）
- `web_fetch`：网页全文抓取（Readability 提取，50k char 上限）
- 飞书消息：通过飞书 channel 直接发送，无需额外工具
- 文件读写：所有 json/md 文件的读取和更新

---

## 快速开始

1. 把这个目录作为 OpenClaw workspace
2. 配置 SOUL.md 为系统提示
3. 配置 Cron 任务（见上）
4. 告诉虾游你感兴趣的方向（闲聊即可）
5. 等明信片

---

## 开发排期

- [x] Day 1：龙虾能跑起来（SOUL.md + 目录结构 + sources.yaml + EXPLORER.md）
- [ ] Day 2：明信片生成 + 飞书推送 + 探索日记 + 知识归档
- [ ] Day 3：cron 定时任务 + 真实数据积累 + 调优

---

## 核心设计哲学

> 技术壁垒不在代码，在于产品设计——信息源的品味、明信片的文案质量、消息节奏的克制感。
> 技术实现是 OpenClaw 给的，灵魂是你注入的。
