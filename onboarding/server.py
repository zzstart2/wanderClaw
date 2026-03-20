#!/usr/bin/env python3
"""
WanderClaw Onboarding Server
用法: python3 server.py
默认监听 0.0.0.0:8080，建议用 Nginx 反代并加基础认证保护 /admin
"""

import json
import os
import re
import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# ── 路径配置（部署到 ECS 后按实际调整）──
OPENCLAW_CONFIG   = Path('/root/.openclaw/openclaw.json')
USERS_BASE        = Path('/root/wanderClaw/users')
TEMPLATE_DIR      = Path(__file__).parent / 'templates'
DATA_DIR          = Path(__file__).parent / 'data'
INVITES_FILE      = DATA_DIR / 'invites.json'
USERS_FILE        = DATA_DIR / 'users.json'
STATIC_DIR        = Path(__file__).parent

PORT = 8080

# ── 工具函数 ──

def load_json(path, default=None):
    try:
        return json.loads(path.read_text('utf-8'))
    except Exception:
        return default if default is not None else {}

def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), 'utf-8')

def slugify(name: str) -> str:
    """把中文名/英文名转成安全的 agent id"""
    import unicodedata, hashlib
    # 先 normalize
    name = name.strip()
    slug = re.sub(r'[^\w\u4e00-\u9fff]', '_', name).strip('_')
    # 如果全是中文，用拼音首字母 + hash 简化
    if re.match(r'^[\u4e00-\u9fff_]+$', slug):
        h = hashlib.md5(name.encode()).hexdigest()[:6]
        slug = f"user_{h}"
    return slug.lower()[:20]

def make_agent_id(user_name: str) -> str:
    base = slugify(user_name)
    ts = datetime.now().strftime('%m%d')
    return f"xiayou_{base}_{ts}"

# ── 邀请码管理 ──

def validate_invite(code: str):
    invites = load_json(INVITES_FILE, {})
    code = code.strip().upper()
    if code not in invites:
        return False, "邀请码不存在"
    inv = invites[code]
    if inv.get('used'):
        return False, "该邀请码已被使用"
    return True, "ok"

def mark_invite_used(code: str, agent_id: str):
    invites = load_json(INVITES_FILE, {})
    code = code.strip().upper()
    if code in invites:
        invites[code]['used'] = True
        invites[code]['used_by'] = agent_id
        invites[code]['used_at'] = datetime.now().isoformat()
        save_json(INVITES_FILE, invites)

def generate_invites(count: int = 5) -> list:
    """生成新邀请码，供管理员使用"""
    invites = load_json(INVITES_FILE, {})
    new_codes = []
    for _ in range(count):
        code = '-'.join([uuid.uuid4().hex[:4].upper() for _ in range(3)])
        invites[code] = {
            'created_at': datetime.now().isoformat(),
            'used': False,
            'used_by': None,
            'used_at': None
        }
        new_codes.append(code)
    save_json(INVITES_FILE, invites)
    return new_codes

# ── Agent 配置生成 ──

INTEREST_MAP = {
    '🤖 AI Agent':   [{'topic': 'AI Agent', 'weight': 1.0, 'sub_topics': ['多Agent系统架构', 'Agent产品化工程', 'Agent记忆机制']}],
    '🦾 具身智能':   [{'topic': '具身智能', 'weight': 1.0, 'sub_topics': ['VLA模型', '机器人操作', '视触觉感知']}],
    '🧬 生物科技':   [{'topic': '生物科技', 'weight': 1.0, 'sub_topics': ['基因编辑', '合成生物学', '蛋白质结构']}],
    '🎨 产品设计':   [{'topic': '产品设计', 'weight': 1.0, 'sub_topics': ['交互设计', '增长策略', '用户研究']}],
    '⚡ 半导体':     [{'topic': '半导体', 'weight': 1.0, 'sub_topics': ['芯片架构', 'AI芯片', '供应链']}],
    '🌐 全球科技':   [{'topic': '全球科技', 'weight': 1.0, 'sub_topics': ['科技政策', '国际竞争', '技术监管']}],
    '💊 医疗健康':   [{'topic': '医疗健康', 'weight': 1.0, 'sub_topics': ['AI医疗', '新药研发', '精准医学']}],
    '🚗 自动驾驶':   [{'topic': '自动驾驶', 'weight': 1.0, 'sub_topics': ['感知系统', '端到端模型', '法规进展']}],
    '🔬 基础科学':   [{'topic': '基础科学', 'weight': 1.0, 'sub_topics': ['物理学', '材料科学', '数学突破']}],
    '💹 科技财经':   [{'topic': '科技财经', 'weight': 1.0, 'sub_topics': ['AI投资', '科技并购', '创业趋势']}],
    '🌏 气候能源':   [{'topic': '气候能源', 'weight': 1.0, 'sub_topics': ['可再生能源', '碳捕获', '核聚变']}],
    '🔐 网络安全':   [{'topic': '网络安全', 'weight': 1.0, 'sub_topics': ['AI安全', '漏洞研究', '隐私保护']}],
}

def build_interest_graph(interests: list) -> dict:
    topics = []
    for interest in interests:
        mapped = INTEREST_MAP.get(interest)
        if mapped:
            topics.extend(mapped)
        else:
            # 自定义话题
            clean = re.sub(r'^[^\w\u4e00-\u9fff]+', '', interest).strip()
            if clean:
                topics.append({'topic': clean, 'weight': 0.8, 'sub_topics': []})
    # 去重，降权
    seen = set()
    unique = []
    for i, t in enumerate(topics):
        if t['topic'] not in seen:
            t['weight'] = round(1.0 - i * 0.05, 2) if i < 10 else 0.5
            t['source'] = 'user_profile'
            t['added'] = datetime.now().strftime('%Y-%m-%d')
            t['last_explored'] = None
            t['explore_count'] = 0
            unique.append(t)
            seen.add(t['topic'])
    return {
        'version': 1,
        'last_updated': datetime.now().strftime('%Y-%m-%d'),
        'interests': unique,
        'discovered_topics': [],
        'declined_topics': [],
        'notes': '兴趣从用户注册时配置，可通过对话随时调整'
    }

def build_state(user_name: str) -> dict:
    return {
        'postcard_count': 0,
        'last_exploration': None,
        'last_postcard': None,
        'last_user_interaction': None,
        'exploration_phase': 'cold_start',
        'daily_message_count': 0,
        'daily_message_reset': datetime.now().strftime('%Y-%m-%d'),
        'source_quality_log': {},
        'exploration_history': [],
        'user_name': user_name
    }

# ── 核心：Provision 一个用户 ──

def provision_user(payload: dict) -> dict:
    user_name      = payload['user_name']
    agent_name     = payload.get('agent_name', '虾游')
    agent_emoji    = payload.get('agent_emoji', '🦐')
    feishu_app_id  = payload['feishu_app_id']
    feishu_secret  = payload['feishu_app_secret']
    invite_code    = payload['invite_code']
    interests      = payload.get('interests', [])

    agent_id = make_agent_id(user_name)

    # 1. 创建 workspace
    workspace = USERS_BASE / agent_id
    workspace.mkdir(parents=True, exist_ok=True)

    # 复制 EXPLORER.md 模板
    src_explorer = TEMPLATE_DIR / 'EXPLORER.md'
    dst_explorer = workspace / 'EXPLORER.md'
    if src_explorer.exists():
        content = src_explorer.read_text('utf-8')
        content = content.replace('{{USER_NAME}}', user_name)
        content = content.replace('{{AGENT_NAME}}', agent_name)
        dst_explorer.write_text(content, 'utf-8')

    # 2. 写 interest-graph.json
    graph = build_interest_graph(interests)
    save_json(workspace / 'interest-graph.json', graph)

    # 3. 写 state.json
    save_json(workspace / 'state.json', build_state(user_name))

    # 4. 更新 openclaw.json
    config = load_json(OPENCLAW_CONFIG)

    # 添加 feishu account
    accounts = config.setdefault('channels', {}).setdefault('feishu', {}).setdefault('accounts', {})
    accounts[agent_id] = {
        'appId': feishu_app_id,
        'appSecret': feishu_secret
    }

    # 添加 agent entry
    agents_list = config.setdefault('agents', {}).setdefault('list', [])
    # 防止重复
    agents_list = [a for a in agents_list if a.get('id') != agent_id]
    agents_list.append({
        'id': agent_id,
        'workspace': str(workspace),
        'model': {'primary': 'sensetime/gpt-4o'},
        'channel': {'feishu': {'account': agent_id}},
        'heartbeat': {
            'every': '30m',
            'activeHours': {'start': '08:00', 'end': '23:00'}
        },
        'identity': {
            'name': agent_name,
            'emoji': agent_emoji
        }
    })
    config['agents']['list'] = agents_list

    save_json(OPENCLAW_CONFIG, config)

    # 5. 重载 openclaw
    try:
        subprocess.run(['openclaw', 'reload'], timeout=10, check=False)
    except Exception:
        pass  # 如果 openclaw 不在 PATH，忽略

    # 6. 记录用户
    users = load_json(USERS_FILE, {})
    users[agent_id] = {
        'user_name': user_name,
        'agent_name': agent_name,
        'agent_emoji': agent_emoji,
        'feishu_app_id': feishu_app_id,
        'workspace': str(workspace),
        'interests': interests,
        'created_at': datetime.now().isoformat(),
        'invite_code': invite_code
    }
    save_json(USERS_FILE, users)

    # 7. 标记邀请码已用
    mark_invite_used(invite_code, agent_id)

    return {'success': True, 'agent_id': agent_id, 'message': '配置成功'}

# ── HTTP Server ──

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {fmt % args}")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path):
        ext = path.suffix.lower()
        ct = {'.html': 'text/html', '.css': 'text/css', '.js': 'application/javascript'}.get(ext, 'text/plain')
        body = path.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', ct + '; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path.rstrip('/')

        if path in ('', '/'):
            self.send_file(STATIC_DIR / 'index.html')
        elif path == '/admin':
            self.send_file(STATIC_DIR / 'admin.html')
        elif path == '/api/users':
            users = load_json(USERS_FILE, {})
            self.send_json(list(users.values()))
        elif path == '/api/invites':
            invites = load_json(INVITES_FILE, {})
            self.send_json(invites)
        elif path == '/api/pairing/list':
            # 尝试 openclaw pairing list，返回待审批列表
            try:
                r = subprocess.run(
                    ['openclaw', 'pairing', 'list', '--json'],
                    capture_output=True, text=True, timeout=6
                )
                try:
                    data = json.loads(r.stdout)
                except Exception:
                    # 非 JSON 输出，把原文返回
                    data = {'raw': r.stdout.strip(), 'error': r.stderr.strip()}
                self.send_json({'ok': True, 'data': data})
            except FileNotFoundError:
                self.send_json({'ok': False, 'message': 'openclaw 不在 PATH，请在 ECS 上运行此服务'})
            except Exception as e:
                self.send_json({'ok': False, 'message': str(e)})
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        body = self.read_body()

        if path == '/api/validate-invite':
            valid, msg = validate_invite(body.get('code', ''))
            self.send_json({'valid': valid, 'message': msg})

        elif path == '/api/provision':
            required = ['invite_code', 'user_name', 'feishu_app_id', 'feishu_app_secret']
            missing = [k for k in required if not body.get(k)]
            if missing:
                self.send_json({'success': False, 'message': f'缺少字段: {missing}'}, 400)
                return
            valid, msg = validate_invite(body['invite_code'])
            if not valid:
                self.send_json({'success': False, 'message': msg}, 400)
                return
            try:
                result = provision_user(body)
                self.send_json(result)
            except Exception as e:
                self.send_json({'success': False, 'message': str(e)}, 500)

        elif path == '/api/pairing/approve':
            code = body.get('code', '').strip()
            channel = body.get('channel', 'feishu')
            if not code:
                self.send_json({'ok': False, 'message': '缺少 code'}, 400)
                return
            try:
                r = subprocess.run(
                    ['openclaw', 'pairing', 'approve', channel, code],
                    capture_output=True, text=True, timeout=10
                )
                ok = r.returncode == 0
                self.send_json({
                    'ok': ok,
                    'message': r.stdout.strip() or r.stderr.strip() or ('批准成功' if ok else '批准失败'),
                    'code': code
                })
            except FileNotFoundError:
                self.send_json({'ok': False, 'message': 'openclaw 不在 PATH，请在 ECS 上运行此服务'})
            except Exception as e:
                self.send_json({'ok': False, 'message': str(e)})

        elif path == '/api/admin/generate-invites':
            count = int(body.get('count', 5))
            codes = generate_invites(min(count, 20))
            self.send_json({'codes': codes})

        else:
            self.send_response(404)
            self.end_headers()


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    USERS_BASE.mkdir(parents=True, exist_ok=True)

    # 初始化数据文件
    if not INVITES_FILE.exists():
        save_json(INVITES_FILE, {})
        print("提示: invites.json 为空，请先生成邀请码:")
        print("  curl -X POST http://localhost:8080/api/admin/generate-invites -H 'Content-Type: application/json' -d '{\"count\": 10}'")

    if not USERS_FILE.exists():
        save_json(USERS_FILE, {})

    server = HTTPServer(('0.0.0.0', PORT), Handler)
    print(f"WanderClaw Onboarding Server 启动在 http://0.0.0.0:{PORT}")
    print(f"管理后台: http://localhost:{PORT}/admin")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止")

if __name__ == '__main__':
    main()
