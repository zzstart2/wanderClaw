#!/bin/bash
# 虾游 (WanderClaw) — 注册定时探索
# 需要 OpenClaw Gateway 运行中

set -e

TZ="${WANDERCLAW_TZ:-Asia/Shanghai}"
STATE_FILE="$HOME/.openclaw/workspace/wanderclaw/state.json"

echo "🦐 注册虾游定时探索任务（时区: $TZ）..."

# ========== 日常 Cron ==========

openclaw cron add \
  --name "虾游晨间探索" \
  --cron "0 9 * * *" --tz "$TZ" \
  --session isolated \
  --timeout 300 \
  --announce --best-effort-deliver \
  --message "按 wanderclaw/EXPLORER.md 六步流程执行一次深度探索。探索完把明信片完整正文回复出来。如果搜索失败，记录日志并正常退出。" \
  2>/dev/null && echo "  ✓ 晨间探索 09:00" || echo "  ✗ 晨间探索注册失败"

openclaw cron add \
  --name "虾游轻度扫描(午)" \
  --cron "0 12 * * *" --tz "$TZ" \
  --session isolated \
  --model minimax-cn/MiniMax-M2.5 \
  --timeout 300 \
  --announce --best-effort-deliver \
  --message "轻度扫描：检查 wanderclaw/sources.yaml 核心水域有无新内容，发现好的写明信片。如果搜索失败，记录日志并正常退出。把明信片完整正文回复出来。" \
  2>/dev/null && echo "  ✓ 午间扫描 12:00" || echo "  ✗ 午间扫描注册失败"

openclaw cron add \
  --name "虾游午后探索" \
  --cron "0 15 * * *" --tz "$TZ" \
  --session isolated \
  --timeout 300 \
  --announce --best-effort-deliver \
  --message "按 wanderclaw/EXPLORER.md 执行一次深度探索。把明信片完整正文回复出来。如果搜索失败，记录日志并正常退出。" \
  2>/dev/null && echo "  ✓ 午后探索 15:00" || echo "  ✗ 午后探索注册失败"

openclaw cron add \
  --name "虾游轻度扫描(晚)" \
  --cron "0 20 * * *" --tz "$TZ" \
  --session isolated \
  --model minimax-cn/MiniMax-M2.5 \
  --timeout 300 \
  --announce --best-effort-deliver \
  --message "晚间轻度扫描，检查有无值得寄明信片的新发现。如果搜索失败，记录日志并正常退出。把明信片完整正文回复出来。" \
  2>/dev/null && echo "  ✓ 晚间扫描 20:00" || echo "  ✗ 晚间扫描注册失败"

# ========== 深潜模式 Cron（周六 22:00）==========

openclaw cron add \
  --name "虾游深潜模式" \
  --cron "0 22 * * 6" --tz "$TZ" \
  --session isolated \
  --timeout 600 \
  --announce --best-effort-deliver \
  --message "【深潜模式】本次为每周一次的深度探索。规则：\n1. 只搜索深度来源（arXiv、Quanta Magazine、Nautilus、Wait But Why）\n2. 优先搜索长文、论文、深度报告\n3. 明信片字数 450-600 字（比平时更详细）\n4. 评分门槛 ≥ 8 才推送（比平时更严格）\n5. 搜索关键词加 'in-depth OR analysis OR long-read OR review OR survey'\n按 wanderclaw/EXPLORER.md 六步流程执行，但应用以上深潜约束。把明信片完整正文回复出来。" \
  2>/dev/null && echo "  ✓ 深潜模式 周六 22:00" || echo "  ✗ 深潜模式注册失败"

# ========== 周度总结 Cron（周日 10:00）==========

openclaw cron add \
  --name "虾游周度总结" \
  --cron "0 10 * * 0" --tz "$TZ" \
  --session isolated \
  --timeout 300 \
  --announce --best-effort-deliver \
  --message "【周度总结】请执行以下步骤：\n1. 读取 wanderclaw/postcards.json，筛选过去 7 天的明信片\n2. 统计：明信片数量、探索方向分布、平均评分\n3. 读取 wanderclaw/state.json 的 feedback_stats（likes/dislikes）\n4. 生成一份简要周报，包含：\n   - 本周明信片数量和精选（评分最高的 1-2 张）\n   - 热门探索方向 Top 3\n   - 用户反馈统计（👍/👎）\n   - 下周探索建议（基于兴趣图谱变化）\n5. 把周报完整正文回复给用户\n格式轻松，用虾游口吻。" \
  2>/dev/null && echo "  ✓ 周度总结 周日 10:00" || echo "  ✗ 周度总结注册失败"

echo "  ✅ 4 个日常 + 1 深潜 + 1 周度总结 任务已注册"

# ========== Cold Start 说明 ==========
# 冷启动三连探索不再通过 at cron 触发（at 定时器有未触发的可靠性问题）。
# 改为 onboarding 流程中由 agent 在当前 session 直接执行三连探索。
# 详见 SKILL.md Step 5。

echo ""
echo "ℹ️  冷启动三连探索由 onboarding 流程直接执行，不需要注册 cron。"
echo "查看任务: openclaw cron list"
