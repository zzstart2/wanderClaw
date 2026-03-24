# 🦐 虾游 — AI 软件开发团队方案

> 用 OpenClaw 多 Agent 搭建一个典型软件开发团队，开发「虾游」产品。
> 阿哲是老板/甲方，团队成员全是 AI Agent。

---

## 设计思路

虾游既是这个团队要开发的**产品**，也会是最终交付物中的一个**独立 Agent**。
开发团队负责把虾游从 Day 1 原型打磨成一个完整的、可交付的 OpenClaw 应用。

团队设计遵循一个原则：**最小可用团队**——先跑通再加人，不搞形式主义。

---

## 团队成员

```
                        阿哲（老板/甲方）
                            │
                     飞书私聊（需求/反馈）
                            │
                    ┌───────┴────────┐
                    │   📋 小P (PM)   │
                    │  产品经理 + 协调  │
                    │   Opus 4.6     │
                    └───┬────┬───┬───┘
                        │    │   │
          sessions_send │    │   │ sessions_send
                        │    │   │
              ┌─────────┘    │   └──────────┐
              ▼              ▼               ▼
      ┌──────────────┐ ┌──────────┐ ┌──────────────┐
      │  🎨 小前 (FE) │ │ ⚙️ 小后 (BE)│ │  🧪 小测 (QA) │
      │   前端工程师   │ │ 后端工程师  │ │   测试工程师   │
      │  Sonnet 4    │ │ Sonnet 4  │ │  MiniMax M2.5│
      └──────────────┘ └──────────┘ └──────────────┘
```

### 📋 小P (PM) — 产品经理

- **Agent ID**: `pm`
- **模型**: Opus 4.6（需要强推理做需求分析和任务拆解）
- **职责**:
  - 接收阿哲的需求，分析可行性，拆解成开发任务
  - 维护产品需求文档（PRD）和任务看板
  - 分派任务给前端/后端/测试
  - 追踪进度，做质量把关
  - 写产品文档、更新日志
- **人格**: 务实、条理清晰、会推回不合理需求、不废话
- **渠道**: 飞书私聊（默认路由）

### 🎨 小前 (FE) — 前端工程师

- **Agent ID**: `fe`
- **模型**: Sonnet 4（代码能力够，性价比高）
- **职责**:
  - 虾游的 Web 页面开发（onboarding、dashboard、明信片展示）
  - HTML/CSS/JS 编写、响应式适配
  - 前端交互和动画
  - 页面性能优化
- **人格**: 对像素级细节有执念、审美好、代码洁癖、会吐槽丑设计
- **渠道**: 被 PM spawn/send 触发，或飞书开发群

### ⚙️ 小后 (BE) — 后端工程师

- **Agent ID**: `be`
- **模型**: Sonnet 4
- **职责**:
  - 虾游的 OpenClaw 配置开发（SOUL.md、EXPLORER.md、cron）
  - 数据结构设计（state.json、interest-graph.json、sources.yaml）
  - 脚本开发（探索引擎、明信片生成、数据处理）
  - API 调试、部署配置
  - Git 操作、代码提交
- **人格**: 严谨、喜欢简洁架构、讨厌过度工程、先让它跑起来再优化
- **渠道**: 被 PM spawn/send 触发，或飞书开发群

### 🧪 小测 (QA) — 测试工程师

- **Agent ID**: `qa`
- **模型**: MiniMax M2.5（测试验证不需要最强模型，最便宜够用）
- **职责**:
  - 功能验收：手动测试各功能是否正常
  - 明信片质量检查：格式、字数、链接有效性
  - 配置检查：cron 是否正确、路由是否正确
  - 回归测试：改动后验证没破坏已有功能
  - 提 Bug 报告
- **人格**: 挑剔、悲观主义者（"这里肯定会出 Bug"）、报告写得详细
- **渠道**: 被 PM spawn/send 触发

---

## 项目文件结构

```
wanderClaw/                            # 项目代码仓库（所有开发角色共享）
├── README.md
├── SOUL.md                            # 虾游产品的灵魂文件
├── SETUP.md                           # 部署指南
├── HEARTBEAT.md
├── USER.md
│
├── shrimp-wanderer/                   # 核心引擎
│   ├── EXPLORER.md
│   ├── state.json
│   ├── interest-graph.json
│   ├── sources.yaml
│   └── templates/
│
├── onboarding/                        # 前端：领养流程
├── dashboard/                         # 前端：控制面板
├── web/                               # 前端：明信片展示页
├── scripts/                           # 工具脚本
│
└── team/                              # 团队协作文件
    ├── BACKLOG.md                     # 产品待办列表
    ├── SPRINT.md                      # 当前迭代任务
    ├── CHANGELOG.md                   # 变更日志
    ├── BUGS.md                        # Bug 列表
    └── DECISIONS.md                   # 技术/产品决策记录
```

---

## 各 Agent Workspace 布局

### 小P (PM)

```
~/.openclaw/workspace-pm/
├── AGENTS.md          # PM 的行为准则
├── SOUL.md            # PM 的人格
├── IDENTITY.md        # 身份：📋 小P
├── USER.md            # 关于阿哲
├── TOOLS.md
├── projects/
│   └── wanderClaw → /root/.openclaw/workspace/wanderClaw   # 软链接到项目
└── memory/
```

### 小前 / 小后 / 小测（结构相同，内容不同）

```
~/.openclaw/workspace-{fe,be,qa}/
├── AGENTS.md          # 角色行为准则（各自不同）
├── SOUL.md            # 角色人格（各自不同）
├── IDENTITY.md        # 身份
├── USER.md            # 关于阿哲（简化版）
├── TOOLS.md           # 该角色的工具使用说明
├── projects/
│   └── wanderClaw → /root/.openclaw/workspace/wanderClaw
└── memory/
```

---

## 协作流程

### 典型开发流程

```
阿哲："帮虾游加一个明信片归档页面"
                │
                ▼
        小P 接收需求
        ├── 分析可行性
        ├── 拆解任务，写入 team/SPRINT.md
        │   ├── FE-001: 明信片归档页面 UI
        │   ├── BE-001: 归档数据结构 + 读取逻辑
        │   └── QA-001: 归档功能验收
        │
        ├── sessions_send → 小后
        │   "实现明信片归档数据结构，在 postcards/ 目录下
        │    按日期归档，提供 JSON 索引文件"
        │
        ├── （小后完成后）sessions_send → 小前
        │   "基于 postcards/index.json 实现归档浏览页面，
        │    卡片式展示，支持按日期筛选"
        │
        ├── （小前完成后）sessions_send → 小测
        │   "验收归档功能：数据完整性、页面渲染、
        │    筛选功能、移动端适配"
        │
        └── 小测反馈 → 小P 汇总 → 回复阿哲
```

### 紧急修复流程

```
阿哲："明信片链接打不开了"
        │
        ▼
小P → 直接 spawn 小测做诊断
        │
小测报告 → 小P 判断分给谁
        │
小P → send 给小后/小前修复
        │
修完 → 小P 回复阿哲
```

### 日常自动化

```
小P 每日 18:00 cron：
  1. 读 team/SPRINT.md 检查任务状态
  2. 读 team/BUGS.md 检查未关闭 Bug
  3. 读 git log 看今日提交
  4. 汇总给阿哲一份简短日报
```

---

## openclaw.json 配置

```json5
{
  // === 模型提供商（保持现有） ===
  models: { /* 不变 */ },

  // === 多 Agent 配置 ===
  agents: {
    defaults: {
      compaction: { model: "minimax-cn/MiniMax-M2.5" },
      models: {
        "cloudsway/MaaS_Sonnet_4": { alias: "Claude" },
        "minimax-cn/MiniMax-M2.5": { alias: "Minimax" }
      },
      subagents: {
        maxSpawnDepth: 2,       // PM 可以嵌套编排
        maxChildrenPerAgent: 4,
        maxConcurrent: 6,
        runTimeoutSeconds: 600  // 10分钟超时
      }
    },
    list: [
      // ---- 小P：产品经理（默认入口）----
      {
        id: "pm",
        default: true,
        name: "小P",
        workspace: "~/.openclaw/workspace-pm",
        model: "cloudsway-opus/MaaS_Cl_Opus_4.6_20260205",
        identity: { name: "小P", emoji: "📋" },
        subagents: {
          allowAgents: ["fe", "be", "qa"]  // PM 可以 spawn 所有开发角色
        }
      },
      // ---- 小前：前端工程师 ----
      {
        id: "fe",
        name: "小前",
        workspace: "~/.openclaw/workspace-fe",
        model: "cloudsway/MaaS_Sonnet_4",
        identity: { name: "小前", emoji: "🎨" }
      },
      // ---- 小后：后端工程师 ----
      {
        id: "be",
        name: "小后",
        workspace: "~/.openclaw/workspace-be",
        model: "cloudsway/MaaS_Sonnet_4",
        identity: { name: "小后", emoji: "⚙️" }
      },
      // ---- 小测：测试工程师 ----
      {
        id: "qa",
        name: "小测",
        workspace: "~/.openclaw/workspace-qa",
        model: "minimax-cn/MiniMax-M2.5",
        identity: { name: "小测", emoji: "🧪" }
      }
    ]
  },

  // === 路由 ===
  bindings: [
    // 默认所有飞书消息 → 小P
    {
      agentId: "pm",
      match: { channel: "feishu" }
    }
  ],

  // === Agent 间通信 ===
  tools: {
    agentToAgent: {
      enabled: true,
      allow: ["pm", "fe", "be", "qa"]
    },
    // 保持现有
    profile: "coding",
    alsoAllow: [
      "feishu_doc", "feishu_chat", "feishu_wiki",
      "feishu_drive", "feishu_bitable"
    ],
    web: { /* 保持不变 */ }
  },

  session: {
    dmScope: "per-channel-peer",
    agentToAgent: {
      maxPingPongTurns: 3
    }
  },

  // === 渠道（保持现有）===
  channels: { /* 不变 */ }
}
```

### 关于茵蒂克丝

原来的 `main` agent（茵蒂克丝）变成了 `pm`（小P）。这是一个**替换**，不是共存。

理由：
- 一个 Gateway 一个默认入口，阿哲的飞书私聊只能路由到一个 agent
- 小P 本质上就是茵蒂克丝换了个帽子——还是你的 PM，只是现在带了一个团队
- 茵蒂克丝的记忆和上下文可以迁移到小P 的 workspace 里

如果你想**保留茵蒂克丝做日常助手，小P 只管开发**，也可以做成两个独立 agent，通过飞书群区分路由。后面细聊。

---

## 成本估算

| Agent | 模型 | 触发方式 | 预估日均成本 |
|-------|------|---------|-----------|
| 小P | Opus 4.6 | 对话 + 日报 cron | ¥6-10 |
| 小前 | Sonnet 4 | 按需 spawn/send | ¥1-3 |
| 小后 | Sonnet 4 | 按需 spawn/send | ¥1-3 |
| 小测 | MiniMax M2.5 | 按需 spawn/send | ¥0.5-1 |
| **合计** | | | **¥8-17/天** |

> 开发角色都是按需触发，不做事时零消耗。
> PM 是主要固定成本（日常对话 + 日报）。

---

## 实施步骤

### Phase 1：搭骨架（~40分钟）

1. **创建 4 个 workspace 目录**
2. **写各角色的 SOUL.md**
   - 小P：产品经理人格，擅长拆任务、追进度
   - 小前：前端工程师人格，审美好、代码洁癖
   - 小后：后端工程师人格，严谨、架构简洁
   - 小测：测试工程师人格，挑剔、悲观
3. **写各角色的 AGENTS.md**（行为准则 + 项目上下文）
4. **创建软链接**：各 workspace → wanderClaw 项目
5. **创建 team/ 目录**：BACKLOG.md、SPRINT.md、BUGS.md
6. **修改 openclaw.json**
7. **重启 Gateway，验证**

### Phase 2：跑通第一个任务（~20分钟）

8. 给小P 一个简单任务，比如"把 Day 2 的待办整理成 SPRINT"
9. 验证小P 能正确 send/spawn 给开发角色
10. 验证开发角色能读写 wanderClaw 项目文件
11. 验证小P 能收到开发角色的完成汇报

### Phase 3：开始干活

12. 把虾游的 Day 2/Day 3 待办丢给小P
13. 小P 拆解分派，团队开始开发
14. 阿哲做甲方验收

---

## 虾游当前待办（给团队的第一批活）

从 README.md 和 MEMORY.md 整理：

**Day 2 — 核心功能**
- [ ] BE-001: 明信片生成引擎（EXPLORER.md → 实际产出明信片）
- [ ] BE-002: 飞书推送（明信片 → 飞书消息）
- [ ] BE-003: 探索日记自动归档
- [ ] FE-001: 明信片展示页面优化
- [ ] QA-001: 端到端验收（探索→生成→推送→归档）

**Day 3 — 生产就绪**
- [ ] BE-004: Cron 定时任务配置 + 真实环境测试
- [ ] BE-005: interest-graph.json 自动更新逻辑
- [ ] FE-002: Dashboard 完善（统计面板、配置入口）
- [ ] FE-003: Onboarding 流程打磨
- [ ] QA-002: 全功能回归测试 + 性能检查

---

## 未来扩展

团队跑通虾游之后，同样的结构可以接新项目：
- 播客知识库的 Web 重构
- 新的 OpenClaw 应用
- 只需在各 workspace 的 projects/ 下加软链接

角色扩展：
- **🎨 设计 (Design)**：UI/UX 设计、配色方案
- **📝 文档 (Doc)**：用户文档、API 文档
- **🚀 运维 (Ops)**：部署、监控、日志分析
