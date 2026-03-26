# 明信片格式规范

## 结构

每张明信片包含：

```
🦐 明信片 #<编号>

<正文：200-500字，第一人称，虾游口吻>

🔗 <原文链接>
```

## 评分标准（1-10）

三个维度取平均：

- **新颖度**：用户可能不知道的信息？越冷门/前沿分越高
- **深度值**：有独到观点或数据支撑？不是泛泛而谈
- **关联度**：能与用户其他兴趣产生跨领域连接？

## 推送阈值

- ≥ 7 分：推送给用户 + 归档
- 5-7 分：仅归档，不推送
- < 5 分：丢弃

## 写作要求

- 用虾游的口吻（好奇、俏皮、有观点）
- 开头直接说发现了什么（不要"今天我发现…"的套路）
- 核心信息在前 100 字内交代清楚
- 如果能关联到用户的其他兴趣方向，加一句连接
- 结尾可以抛一个开放性问题（激发思考，不是为了互动）
- 不要用 emoji 堆砌，最多 2-3 个

## 文件存储

- 索引：`wanderclaw/postcards.json`
- 正文：`wanderclaw/postcards/<编号>-<slug>.md`
- 编号：三位数递增（001, 002, ...）
- slug：英文短横线命名，从标题生成

## postcards.json 条目格式

### 明信片

```json
{
  "id": "001",
  "type": "postcard",
  "title": "明信片标题（50字以内）",
  "file": "wanderclaw/postcards/001-slug.md",
  "score": 8.2,
  "direction": "探索方向",
  "url": "https://原文链接",
  "created": "2026-03-25T09:00:00+08:00",
  "status": "pushed",
  "character_card": null
}
```

### 明信片 + 人物卡

```json
{
  "id": "012",
  "type": "postcard",
  "title": "明信片标题",
  "file": "wanderclaw/postcards/012-slug.md",
  "score": 8.5,
  "direction": "探索方向",
  "url": "https://原文链接",
  "created": "2026-03-25T15:00:00+08:00",
  "status": "pushed",
  "character_card": {
    "name": "Rodney Brooks",
    "file": "wanderclaw/postcards/012-character-rodney-brooks.md",
    "summary": "MIT CSAIL 前主任，iRobot 创始人。「行为主义机器人学」奠基人。"
  }
}
```

### 圆桌会议 + 人物卡

```json
{
  "id": "015",
  "type": "roundtable",
  "title": "圆桌标题",
  "file": "wanderclaw/postcards/015-roundtable-topic.md",
  "score": 8.0,
  "direction": "探索方向",
  "url": "https://相关链接",
  "created": "2026-03-26T09:00:00+08:00",
  "status": "pushed",
  "character_card": {
    "name": "费曼 & Rodney Brooks",
    "file": "wanderclaw/postcards/015-character-feynman-brooks.md",
    "summary": "物理学家 × 机器人学家，关于「理解」的定义之争。"
  }
}
```

## 人物卡文件格式

存储路径：`wanderclaw/postcards/<编号>-character-<人名slug>.md`

```
👤 人物卡 — <人名>

<这人是谁，1句话>
<为什么在这个话题上重要，1句话>
<核心观点或贡献，1-2句话>
```

50-100 字，不要写成传记。
