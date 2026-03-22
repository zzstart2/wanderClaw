# 虾游开发工具

## preview-postcard.py — 明信片预览与调试

快速预览明信片在不同类型、不同字数下的效果，同时生成飞书卡片 JSON 和 HTML 预览。

### 用法

```bash
# 生成全部类型的样例（推荐先跑一次看效果）
python3 scripts/preview-postcard.py --demo

# 自定义内容
python3 scripts/preview-postcard.py \
  --type 普通 \
  --number 12 \
  --content "你想测试的明信片内容" \
  --link "https://example.com"

# 从已有的明信片 markdown 文件加载
python3 scripts/preview-postcard.py --from-file shrimp-wanderer/postcards/012-xxx.md

# 交互模式（不加任何参数）
python3 scripts/preview-postcard.py
```

### 输出

| 输出 | 路径 | 说明 |
|------|------|------|
| 终端预览 | stdout | 带颜色的终端渲染，含字数统计和合规检查 |
| 飞书卡片 JSON | `scripts/preview-output/postcard-XXX.json` | 可粘贴到[飞书消息卡片搭建工具](https://open.feishu.cn/tool/cardbuilder)验证 |
| HTML 预览 | `scripts/preview-output/preview.html` | 浏览器打开查看近似视觉效果 |

### 字数限制

| 类型 | 正文上限 |
|------|----------|
| 🦐 普通 | 80字 |
| ✨ 惊喜 | 150字 |
| 🌟 宝藏 | 250字 |
| 🎁 彩蛋 | 40字 |

超出限制会在终端和HTML中标红警告。

### 飞书卡片模板

模板文件：`shrimp-wanderer/templates/postcard-card.json`

四种类型对应四种配色：
- 普通 → turquoise（青色）
- 惊喜 → violet（紫色）
- 宝藏 → gold（金色）
- 彩蛋 → carmine（红色）
