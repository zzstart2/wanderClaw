#!/usr/bin/env python3
"""
虾游明信片预览工具

用法：
  # 交互式：手动输入内容
  python3 preview-postcard.py

  # 命令行参数
  python3 preview-postcard.py --type 普通 --number 12 \
    --content "DeepMind 偷偷发了篇论文，用 LLM 自己给自己写测试用例。等等，这不就是 AI 在给自己做单元测试吗？" \
    --link "https://arxiv.org/abs/xxxx"

  # 从 markdown 文件加载
  python3 preview-postcard.py --from postcards/012-deepmind-test.md

  # 生成全部类型的样例
  python3 preview-postcard.py --demo

输出：
  1. 终端预览（纯文本渲染）
  2. JSON 文件（可直接粘贴到飞书消息卡片搭建工具验证）
  3. HTML 预览文件（浏览器打开查看近似效果）
"""

import json
import argparse
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = PROJECT_DIR / "shrimp-wanderer" / "templates" / "postcard-card.json"
OUTPUT_DIR = PROJECT_DIR / "scripts" / "preview-output"

# 卡片颜色映射（终端ANSI + HTML）
CARD_STYLES = {
    "普通": {"emoji": "🦐", "ansi": "\033[36m", "html_color": "#2ecfcf", "template": "turquoise"},
    "惊喜": {"emoji": "✨", "ansi": "\033[35m", "html_color": "#9b6fe0", "template": "violet"},
    "宝藏": {"emoji": "🌟", "ansi": "\033[33m", "html_color": "#e0a84f", "template": "gold"},
    "彩蛋": {"emoji": "🎁", "ansi": "\033[31m", "html_color": "#e06060", "template": "carmine"},
}

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# 字数限制
WORD_LIMITS = {"普通": 80, "惊喜": 150, "宝藏": 250, "彩蛋": 40}

DEMO_POSTCARDS = [
    {
        "type": "普通",
        "number": 12,
        "content": "DeepMind 偷偷发了篇论文，用 LLM 自己给自己写测试用例，然后自己跑通了。等等，这不就是 AI 在给自己做单元测试吗？",
        "link": "https://arxiv.org/abs/2406.xxxx",
    },
    {
        "type": "惊喜",
        "number": 23,
        "content": "翻到一个冷门数据：全球70%的海运保险还在用1906年的法律框架。一百多年了。有些行业的\"AI改造\"可能要从改法律开始。跟 #008 那张讲的\"制度是最慢的基础设施\"完全对上了。",
        "link": "https://ft.com/content/xxxx",
    },
    {
        "type": "宝藏",
        "number": 37,
        "content": "随手点进一个链接，结果看了一小时。这人把认知科学和编程语言设计串起来了，核心观点是：好的 API 设计本质上是在设计人的心智模型。他用了一个特别妙的类比——API 文档就是\"认知脚手架\"，你搭得好，用户就能自己盖楼；搭得烂，用户连门都找不到。跟 #015 那张讲的\"界面即认知\"完全对上了。",
        "link": "https://nautil.us/xxxx",
    },
    {
        "type": "彩蛋",
        "number": 41,
        "content": "章鱼有三个心脏。其中两个在游泳时会停跳。所以章鱼讨厌游泳。",
        "link": "https://en.wikipedia.org/wiki/Octopus",
    },
]


def load_template():
    """加载飞书卡片模板"""
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def count_chars(text):
    """计算正文字数（中文算1，英文单词算1）"""
    return len(text)


def render_terminal(card_type, number, content, link):
    """终端预览"""
    style = CARD_STYLES[card_type]
    limit = WORD_LIMITS[card_type]
    char_count = count_chars(content)
    over = char_count > limit

    print()
    print(f"  {style['ansi']}{'━' * 50}{RESET}")
    print(f"  {style['ansi']}{BOLD}  {style['emoji']} 明信片 #{number:03d}{RESET}")
    print(f"  {style['ansi']}{'━' * 50}{RESET}")
    print()

    # 正文，每行缩进
    lines = content.split("\n")
    for line in lines:
        print(f"    {line}")
    print()

    print(f"    {DIM}🔗 {link}{RESET}")
    print()

    # 字数统计
    status = f"\033[31m⚠ 超出 {char_count - limit} 字！\033[0m" if over else "\033[32m✓ 合规\033[0m"
    print(f"  {DIM}[{card_type}明信片 | {char_count}/{limit}字 | {status}]{RESET}")
    print(f"  {style['ansi']}{'━' * 50}{RESET}")
    print()


def render_feishu_card(card_type, number, content, link):
    """生成飞书消息卡片 JSON"""
    templates = load_template()
    type_map = {"普通": "普通明信片", "惊喜": "惊喜明信片", "宝藏": "宝藏明信片", "彩蛋": "彩蛋明信片"}
    template = json.loads(json.dumps(templates[type_map[card_type]]))

    # 替换变量（直接操作dict，避免JSON转义问题）
    def replace_in_obj(obj, replacements):
        if isinstance(obj, str):
            for k, v in replacements.items():
                obj = obj.replace(k, v)
            return obj
        elif isinstance(obj, dict):
            return {k: replace_in_obj(v, replacements) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [replace_in_obj(item, replacements) for item in obj]
        return obj

    replacements = {
        "{{number}}": f"{number:03d}",
        "{{content}}": content,
        "{{link}}": link,
    }
    return replace_in_obj(template, replacements)


def render_html(postcards):
    """生成 HTML 预览页面"""
    cards_html = ""
    for pc in postcards:
        style = CARD_STYLES[pc["type"]]
        limit = WORD_LIMITS[pc["type"]]
        char_count = count_chars(pc["content"])
        over = char_count > limit

        status_html = (
            f'<span style="color:#ff6b6b">⚠ 超出 {char_count - limit} 字</span>'
            if over
            else '<span style="color:#62d9a0">✓ 合规</span>'
        )

        cards_html += f"""
        <div class="card" style="border-left: 3px solid {style['html_color']}">
          <div class="card-header" style="color: {style['html_color']}">
            {style['emoji']} 明信片 #{pc['number']:03d}
          </div>
          <div class="card-body">
            {pc['content']}
          </div>
          <div class="card-link">
            <a href="{pc['link']}" target="_blank">🔗 {pc['link'][:60]}{'...' if len(pc['link']) > 60 else ''}</a>
          </div>
          <div class="card-meta">
            {pc['type']}明信片 | {char_count}/{limit}字 | {status_html}
          </div>
        </div>
        """

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>🦐 虾游明信片预览</title>
  <style>
    body {{
      background: #0f0f13;
      color: #e2e2f0;
      font-family: -apple-system, 'PingFang SC', sans-serif;
      max-width: 480px;
      margin: 40px auto;
      padding: 0 20px;
    }}
    h1 {{
      text-align: center;
      font-size: 20px;
      margin-bottom: 30px;
      color: #8888aa;
    }}
    .card {{
      background: #17171e;
      border-radius: 8px;
      padding: 16px 20px;
      margin-bottom: 20px;
    }}
    .card-header {{
      font-size: 15px;
      font-weight: 600;
      margin-bottom: 12px;
    }}
    .card-body {{
      font-size: 14px;
      line-height: 1.7;
      color: #d0d0e0;
      margin-bottom: 12px;
    }}
    .card-link {{
      padding: 8px 0;
      border-top: 1px solid #2a2a38;
    }}
    .card-link a {{
      color: #5eb8ff;
      text-decoration: none;
      font-size: 13px;
    }}
    .card-link a:hover {{ text-decoration: underline; }}
    .card-meta {{
      font-size: 11px;
      color: #555570;
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px solid #2a2a38;
    }}
  </style>
</head>
<body>
  <h1>🦐 虾游明信片预览</h1>
  {cards_html}
  <p style="text-align:center; color:#555570; font-size:12px; margin-top:40px">
    预览生成于本地 · 实际飞书卡片样式会有差异
  </p>
</body>
</html>"""


def parse_postcard_file(filepath):
    """从 markdown 明信片文件解析内容"""
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    # 尝试提取编号
    import re
    number_match = re.search(r"#(\d+)", text)
    number = int(number_match.group(1)) if number_match else 0

    # 提取链接
    link_match = re.search(r"🔗\s*(https?://\S+)", text)
    link = link_match.group(1) if link_match else "https://example.com"

    # 提取正文（去掉标题行和链接行）
    lines = text.strip().split("\n")
    content_lines = []
    for line in lines:
        if line.startswith("🦐") or line.startswith("✨") or line.startswith("🌟") or line.startswith("🎁"):
            continue
        if line.startswith("🔗"):
            continue
        if line.strip() == "":
            continue
        content_lines.append(line.strip())
    content = " ".join(content_lines)

    return {"number": number, "content": content, "link": link}


def main():
    parser = argparse.ArgumentParser(description="🦐 虾游明信片预览工具")
    parser.add_argument("--type", choices=["普通", "惊喜", "宝藏", "彩蛋"], default="普通", help="明信片类型")
    parser.add_argument("--number", type=int, default=1, help="明信片编号")
    parser.add_argument("--content", type=str, help="明信片正文")
    parser.add_argument("--link", type=str, default="https://example.com", help="原文链接")
    parser.add_argument("--from-file", type=str, help="从 markdown 文件加载明信片")
    parser.add_argument("--demo", action="store_true", help="生成全部类型的样例预览")
    parser.add_argument("--html", action="store_true", help="同时生成 HTML 预览")
    parser.add_argument("--json", action="store_true", help="同时输出飞书卡片 JSON")

    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    postcards = []

    if args.demo:
        postcards = DEMO_POSTCARDS
        args.html = True
        args.json = True
    elif args.from_file:
        parsed = parse_postcard_file(args.from_file)
        postcards = [{"type": args.type, **parsed}]
    elif args.content:
        postcards = [{"type": args.type, "number": args.number, "content": args.content, "link": args.link}]
    else:
        # 交互模式
        print("\n🦐 虾游明信片预览工具\n")
        print("类型：1=普通  2=惊喜  3=宝藏  4=彩蛋")
        type_input = input("选择类型 [1]: ").strip() or "1"
        type_map = {"1": "普通", "2": "惊喜", "3": "宝藏", "4": "彩蛋"}
        card_type = type_map.get(type_input, "普通")

        number = int(input("编号 [1]: ").strip() or "1")
        print("输入正文（多行以空行结束）：")
        lines = []
        while True:
            line = input()
            if line == "":
                break
            lines.append(line)
        content = "\n".join(lines)
        link = input("链接 [https://example.com]: ").strip() or "https://example.com"

        postcards = [{"type": card_type, "number": number, "content": content, "link": link}]
        args.html = True
        args.json = True

    # 终端预览
    for pc in postcards:
        render_terminal(pc["type"], pc["number"], pc["content"], pc["link"])

    # JSON 输出
    if args.json:
        for pc in postcards:
            card = render_feishu_card(pc["type"], pc["number"], pc["content"], pc["link"])
            json_path = OUTPUT_DIR / f"postcard-{pc['number']:03d}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(card, f, ensure_ascii=False, indent=2)
            print(f"  📄 飞书卡片 JSON → {json_path}")

    # HTML 预览
    if args.html:
        html = render_html(postcards)
        html_path = OUTPUT_DIR / "preview.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  🌐 HTML 预览 → {html_path}")

    print()


if __name__ == "__main__":
    main()
