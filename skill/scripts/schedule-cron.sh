#!/bin/bash
# 虾游 (WanderClaw) — 注册定时探索 + Cold Start 三连探索
# 需要 OpenClaw Gateway 运行中

set -e

TZ="${WANDERCLAW_TZ:-Asia/Shanghai}"
STATE_FILE="$HOME/.openclaw/workspace/wanderclaw/state.json"

echo "🦐 注册虾游定时探索任务（时区: $TZ）..."

# 检查日常 cron 是否存在，如果不存在则注册
daily_exists=$(openclaw cron list 2>/dev/null | grep -c "虾游晨间探索" || true)
if [ "$daily_exists" -eq 0 ]; then

# ========== 日常 Cron ==========

openclaw cron add \
  --name "虾游晨间探索" \
  --cron "0 9 * * *" --tz "$TZ" \
  --session isolated \
  --announce --channel last \
  --message "读取 wanderclaw/state.json 和 wanderclaw/interest-graph.json，按 wanderclaw/EXPLORER.md 的六步流程执行一次深度探索。探索完把明信片完整正文回复出来。" \
  2>/dev/null && echo "  ✓ 晨间探索 09:00" || echo "  ✗ 晨间探索注册失败"

openclaw cron add \
  --name "虾游轻度扫描(午)" \
  --cron "0 12 * * *" --tz "$TZ" \
  --session isolated \
  --model sonnet \
  --announce --channel last \
  --message "执行一次轻度扫描：只检查 wanderclaw/sources.yaml 核心水域的信息源有无新内容，发现好的写明信片。把明信片完整正文回复出来。" \
  2>/dev/null && echo "  ✓ 午间扫描 12:00" || echo "  ✗ 午间扫描注册失败"

openclaw cron add \
  --name "虾游午后探索" \
  --cron "0 15 * * *" --tz "$TZ" \
  --session isolated \
  --announce --channel last \
  --message "执行一次深度探索，参考 wanderclaw/EXPLORER.md。把明信片完整正文回复出来。" \
  2>/dev/null && echo "  ✓ 午后探索 15:00" || echo "  ✗ 午后探索注册失败"

openclaw cron add \
  --name "虾游轻度扫描(晚)" \
  --cron "0 20 * * *" --tz "$TZ" \
  --session isolated \
  --model sonnet \
  --announce --channel last \
  --message "执行一次晚间轻度扫描，检查有无值得寄明信片的新发现。把明信片完整正文回复出来。" \
  2>/dev/null && echo "  ✓ 晚间扫描 20:00" || echo "  ✗ 晚间扫描注册失败"

  echo "  ✅ 4 个日常探索任务已注册"
else
  echo "  ℹ️  日常 cron 已存在，跳过"
fi

# ========== Cold Start 三连探索 ==========
# 检查是否需要三连探索

PROGRESS=0
if [ -f "$STATE_FILE" ]; then
  PROGRESS=$(python3 -c "import json; print(json.load(open('$STATE_FILE')).get('cold_start_progress', 0))" 2>/dev/null || echo "0")
fi

if [ "$PROGRESS" -ge 3 ]; then
  echo "  ℹ️  三连探索已完成（progress=$PROGRESS），跳过"
else
  echo ""
  echo "🚀 注册 Cold Start 三连探索..."

  # 第 1 次：30秒后
  if [ "$PROGRESS" -lt 1 ]; then
    openclaw cron add \
      --name "虾游冷启动-第1次" \
      --at "30s" \
      --delete-after-run \
      --session isolated \
      --timeout 120 \
      --announce --channel last \
      --message "【虾游冷启动探索 第1次】
读取 wanderclaw/state.json 的 cold_start_progress。如果已 >= 1 则回复「已完成」并停止。
否则执行 1 次探索：
1. 读 wanderclaw/interest-graph.json，选权重最高的兴趣方向
2. web_search 搜 2-3 组关键词（核心水域：arXiv, HN, Quanta）
3. web_fetch 最佳 2 个 URL 获取正文
4. 用虾游口吻写明信片，保存到 wanderclaw/postcards/pc-001.md
5. 读 wanderclaw/postcards.json → 追加 {\"id\":\"pc-001\",\"title\":\"...\",\"domain\":\"...\",\"date\":\"...\",\"url\":\"...\"} → 写回
6. 读 wanderclaw/state.json → 设 cold_start_progress=1, postcard_count=1 → 写回
7. 把 pc-001.md 的完整内容（标题+正文+链接）回复出来
只做这 1 次，做完停止。" \
      2>/dev/null && echo "  ✓ 冷启动第1次 +30s" || echo "  ✗ 冷启动第1次注册失败"
  fi

  # 第 2 次：4分钟后
  if [ "$PROGRESS" -lt 2 ]; then
    openclaw cron add \
      --name "虾游冷启动-第2次" \
      --at "4m" \
      --delete-after-run \
      --session isolated \
      --timeout 120 \
      --announce --channel last \
      --message "【虾游冷启动探索 第2次】
读取 wanderclaw/state.json 的 cold_start_progress。如果已 >= 2 则回复「已完成」并停止。
否则执行 1 次探索（选和第1次不同的兴趣方向，尝试跨领域交叉）：
1. 读 wanderclaw/interest-graph.json，选第二个兴趣方向
2. web_search 搜 2-3 组关键词
3. web_fetch 最佳 2 个 URL
4. 用虾游口吻写明信片，保存到 wanderclaw/postcards/pc-002.md
5. 读 wanderclaw/postcards.json → 追加 → 写回
6. 读 wanderclaw/state.json → 设 cold_start_progress=2, postcard_count=2 → 写回
7. 把 pc-002.md 完整内容回复出来
只做这 1 次，做完停止。" \
      2>/dev/null && echo "  ✓ 冷启动第2次 +4m" || echo "  ✗ 冷启动第2次注册失败"
  fi

  # 第 3 次：8分钟后
  if [ "$PROGRESS" -lt 3 ]; then
    openclaw cron add \
      --name "虾游冷启动-第3次" \
      --at "8m" \
      --delete-after-run \
      --session isolated \
      --timeout 120 \
      --announce --channel last \
      --message "【虾游冷启动探索 第3次 - 惊喜】
读取 wanderclaw/state.json 的 cold_start_progress。如果已 >= 3 则回复「已完成」并停止。
否则执行 1 次惊喜探索（不按用户兴趣，随机选方向：科学发现、历史趣闻、前沿技术等）：
1. 随机选一个意外方向
2. web_search 搜 2-3 组关键词
3. web_fetch 最佳 2 个 URL
4. 用虾游口吻写明信片，保存到 wanderclaw/postcards/pc-003.md
5. 读 wanderclaw/postcards.json → 追加 → 写回
6. 读 wanderclaw/state.json → 设 cold_start_progress=3, postcard_count=3 → 写回
7. 把 pc-003.md 完整内容回复出来
只做这 1 次，做完停止。" \
      2>/dev/null && echo "  ✓ 冷启动第3次 +8m" || echo "  ✗ 冷启动第3次注册失败"
  fi

  echo "  ✅ 三连探索将在 30秒/4分钟/8分钟后自动触发"
fi

echo ""
echo "查看任务: openclaw cron list"
