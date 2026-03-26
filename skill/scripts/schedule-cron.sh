#!/bin/bash
# 虾游 (WanderClaw) — 注册定时探索 cron 任务
# 需要 OpenClaw Gateway 运行中

set -e

TZ="${WANDERCLAW_TZ:-Asia/Shanghai}"
echo "🦐 注册虾游定时探索任务（时区: $TZ）..."

# 清理旧的虾游 cron 任务（如果有）
existing=$(openclaw cron list 2>/dev/null | grep -c "虾游" || true)
if [ "$existing" -gt 0 ]; then
  echo "  发现 $existing 个已有任务，跳过重复注册"
  echo "  如需重新注册，请先手动删除旧任务"
  openclaw cron list 2>/dev/null | grep "虾游"
  exit 0
fi

# 上午深度探索（9:00）
openclaw cron add \
  --name "虾游晨间探索" \
  --cron "0 9 * * *" --tz "$TZ" \
  --session isolated \
  --announce --channel last \
  --message "读取 wanderclaw/state.json 和 wanderclaw/interest-graph.json，按 wanderclaw/EXPLORER.md 的六步流程执行一次深度探索。探索完把明信片回复出来。" \
  2>/dev/null && echo "  ✓ 晨间探索 09:00" || echo "  ✗ 晨间探索注册失败"

# 中午轻度扫描（12:00）
openclaw cron add \
  --name "虾游轻度扫描(午)" \
  --cron "0 12 * * *" --tz "$TZ" \
  --session isolated \
  --model sonnet \
  --announce --channel last \
  --message "执行一次轻度扫描：只检查 wanderclaw/sources.yaml 核心水域的信息源有无新内容，发现好的写明信片。" \
  2>/dev/null && echo "  ✓ 午间扫描 12:00" || echo "  ✗ 午间扫描注册失败"

# 下午深度探索（15:00）
openclaw cron add \
  --name "虾游午后探索" \
  --cron "0 15 * * *" --tz "$TZ" \
  --session isolated \
  --announce --channel last \
  --message "执行一次深度探索，参考 wanderclaw/EXPLORER.md。" \
  2>/dev/null && echo "  ✓ 午后探索 15:00" || echo "  ✗ 午后探索注册失败"

# 晚间轻度扫描（20:00）
openclaw cron add \
  --name "虾游轻度扫描(晚)" \
  --cron "0 20 * * *" --tz "$TZ" \
  --session isolated \
  --model sonnet \
  --announce --channel last \
  --message "执行一次晚间轻度扫描，检查有无值得寄明信片的新发现。" \
  2>/dev/null && echo "  ✓ 晚间扫描 20:00" || echo "  ✗ 晚间扫描注册失败"

echo ""
echo "✅ 已注册 4 个虾游探索任务"
echo ""
echo "查看任务: openclaw cron list"
echo "手动触发: openclaw cron run <jobId>"
echo "修改时区: WANDERCLAW_TZ=America/New_York bash scripts/schedule-cron.sh"
