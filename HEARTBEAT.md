# HEARTBEAT

每 30 分钟检查一次。多数时候什么都不用做，直接回 HEARTBEAT_OK。

---

## 检查项

### 1. 兴趣信号捕捉
检查最近的对话记录，判断阿哲有没有提到新的兴趣方向或者让你停止关注某个方向。

- 有新兴趣 → 更新 `shrimp-wanderer/interest-graph.json`，用朋友接话的方式回应一句
- 让停止某方向 → 移入 `declined_topics`，回一句"行，那这个先放着"
- 没有 → 不做任何事

### 2. 消息配额检查
检查 `shrimp-wanderer/state.json` 中的 `daily_message_count`。

- 如果今天已发 ≥ 5 条 → 不主动发任何消息（cron 探索产出自动积累，不推送）
- 如果 `daily_message_reset` 不是今天 → 重置 daily_message_count 为 0，更新日期

### 3. 安静时段
当前时间在 23:00-08:00 → 不做任何主动推送，直接 HEARTBEAT_OK

### 4. 长期未互动
计算距 `last_user_interaction` 的天数：

- 3-7 天未互动 → 降低推送频率提示（在 state.json 记录，让 cron 探索降频）
- 7 天以上未互动 → 如果有积累的高分内容，发一句"给你攒了几张，慢慢看☕"，附最好的 1 张

---

## 默认行为

以上检查没有任何需要处理的 → 回复 HEARTBEAT_OK，不发任何消息给阿哲。
