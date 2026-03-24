#!/usr/bin/env python3
"""
WanderClaw Onboarding + Chat Server
用法: python3 server.py
监听 0.0.0.0:8080
"""

import json, os, re, shutil, subprocess, uuid, threading, queue as q_mod
import hashlib, secrets, time, urllib.request
from datetime import datetime
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs

# ── 路径配置（支持环境变量，兼容本地开发和 ECS）──
_HERE = Path(__file__).parent

# ECS 默认路径；本地开发可通过环境变量覆盖
OPENCLAW_CONFIG = Path(os.environ.get('OPENCLAW_CONFIG',
    str(_HERE.parent.parent / '.openclaw' / 'openclaw.json')
    if not Path('/root/.openclaw/openclaw.json').exists()
    else '/root/.openclaw/openclaw.json'))

USERS_BASE = Path(os.environ.get('WANDERCLAW_USERS_BASE',
    str(_HERE / 'local_users')
    if not Path('/root/wanderClaw/users').exists()
    else '/root/wanderClaw/users'))

TEMPLATE_DIR = _HERE / 'templates'
DATA_DIR     = _HERE / 'data'
STATIC_DIR   = _HERE
INVITES_FILE  = DATA_DIR / 'invites.json'
USERS_FILE    = DATA_DIR / 'users.json'
SESSIONS_FILE = DATA_DIR / 'sessions.json'
MESSAGES_DIR  = DATA_DIR / 'messages'
PORT = int(os.environ.get('PORT', 8080))

# 本地模式：openclaw 不可用时降级
_OPENCLAW_AVAILABLE = bool(shutil.which('openclaw'))

ADMIN_TOKEN = os.environ.get('WANDERCLAW_ADMIN_TOKEN', 'wanderclaw-admin-2026')

# ── JSON 工具 ──
def load_json(path, default=None):
    try: return json.loads(Path(path).read_text('utf-8'))
    except Exception: return default if default is not None else {}

def save_json(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), 'utf-8')

# ── Slugify ──
def slugify(name):
    slug = re.sub(r'[^\w\u4e00-\u9fff]', '_', name.strip()).strip('_')
    if re.match(r'^[\u4e00-\u9fff_]+$', slug):
        slug = 'user_' + hashlib.md5(name.encode()).hexdigest()[:6]
    return slug.lower()[:20]

def make_agent_id(user_name):
    return f"xiayou_{slugify(user_name)}_{datetime.now().strftime('%m%d')}"

# ════════════════════════════════════════
# ── 认证 ──
# ════════════════════════════════════════

def hash_password(password, salt=None):
    if salt is None: salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100_000)
    return h.hex(), salt

def verify_password(password, stored_hash, salt):
    h, _ = hash_password(password, salt)
    return secrets.compare_digest(h, stored_hash)

def create_session(user_id, remember=False):
    token = secrets.token_hex(32)
    sessions = load_json(SESSIONS_FILE, {})
    expires = time.time() + (30 * 86400 if remember else 86400)
    sessions[token] = {
        'user_id': user_id,
        'expires': expires,
        'created': datetime.now().isoformat()
    }
    save_json(SESSIONS_FILE, sessions)
    return token

def validate_token(token):
    if not token: return None
    sessions = load_json(SESSIONS_FILE, {})
    s = sessions.get(token)
    if not s: return None
    if s.get('expires') and time.time() > s['expires']: return None
    return s.get('user_id')

def find_user_by_name(name):
    """返回 (user_id, user_info) 或 None"""
    users = load_json(USERS_FILE, {})
    name_lower = name.strip().lower()
    for uid, u in users.items():
        if u.get('user_name', '').lower() == name_lower:
            return uid, u
    return None, None

def get_user(user_id):
    users = load_json(USERS_FILE, {})
    return users.get(user_id)

# ════════════════════════════════════════
# ── 消息存储 ──
# ════════════════════════════════════════

def store_message(user_id, msg_data):
    MESSAGES_DIR.mkdir(parents=True, exist_ok=True)
    f = MESSAGES_DIR / f'{user_id}.json'
    msgs = load_json(f, [])
    if 'id' not in msg_data:
        msg_data['id'] = 'msg_' + secrets.token_hex(6)
    if 'timestamp' not in msg_data:
        msg_data['timestamp'] = datetime.now().isoformat()
    msgs.append(msg_data)
    save_json(f, msgs)
    return msg_data

def get_messages(user_id, limit=100):
    f = MESSAGES_DIR / f'{user_id}.json'
    return load_json(f, [])[-limit:]

def send_to_agent(user_id, content, user_info):
    """调用 openclaw agent 触发对话，异步捕获回复写入 outbox"""
    if not _OPENCLAW_AVAILABLE:
        print(f"[send_to_agent] openclaw 不可用（本地模式），跳过 agent 调用")
        return False
    agent_id = user_info.get('agent_id', user_id)
    workspace = Path(user_info.get('workspace', ''))

    def _run():
        try:
            r = subprocess.run(
                ['openclaw', 'agent', '--agent', agent_id, '-m', content, '--json'],
                capture_output=True, text=True, timeout=120
            )
            if r.returncode != 0:
                print(f"[send_to_agent] openclaw 返回非零: {r.returncode}\nstderr: {r.stderr[:200]}")
                return
            # openclaw 的 plugin 注册消息也输出到 stdout，需要找到 JSON 部分
            raw = r.stdout
            json_start = raw.find('{')
            if json_start == -1:
                print(f"[send_to_agent] stdout 中无 JSON: {raw[:200]}")
                return
            resp = json.loads(raw[json_start:])
            payloads = resp.get('result', {}).get('payloads', [])
            for p in payloads:
                text = p.get('text', '').strip()
                if not text:
                    continue
                # 写入 outbox，outbox_poller 会自动推送给前端
                outbox_f = workspace / 'outbox.json'
                outbox = load_json(outbox_f, [])
                outbox.append({
                    'type': 'message',
                    'from': 'agent',
                    'content': text,
                    'timestamp': datetime.now().isoformat()
                })
                save_json(outbox_f, outbox)
                print(f"[send_to_agent] 回复已写入 outbox: {text[:60]}")
        except Exception as e:
            print(f"[send_to_agent] 异常: {e}")

    threading.Thread(target=_run, daemon=True, name=f'AgentCall-{agent_id}').start()
    return True

# ════════════════════════════════════════
# ── SSE 基础设施 ──
# ════════════════════════════════════════

_sse_clients: dict = {}   # user_id -> list[queue.Queue]
_sse_lock = threading.Lock()

def register_sse(user_id):
    client_q = q_mod.Queue()
    with _sse_lock:
        _sse_clients.setdefault(user_id, []).append(client_q)
    return client_q

def unregister_sse(user_id, client_q):
    with _sse_lock:
        if user_id in _sse_clients:
            try: _sse_clients[user_id].remove(client_q)
            except ValueError: pass

def push_sse(user_id, event: dict):
    data = json.dumps(event, ensure_ascii=False)
    with _sse_lock:
        queues = list(_sse_clients.get(user_id, []))
    for cq in queues:
        try: cq.put_nowait(data)
        except Exception: pass

# ════════════════════════════════════════
# ── Outbox 轮询线程 ──
# ════════════════════════════════════════

def outbox_poller():
    """每 3 秒检查所有用户 workspace 的 outbox.json，有消息则推送"""
    while True:
        try:
            users = load_json(USERS_FILE, {})
            for user_id, u in users.items():
                workspace = Path(u.get('workspace', ''))
                outbox_f = workspace / 'outbox.json'
                if not outbox_f.exists(): continue
                try:
                    msgs = load_json(outbox_f, [])
                    if not msgs: continue
                    # 先清空，再处理（防止重复）
                    save_json(outbox_f, [])
                    for msg in msgs:
                        # Skip user-originated messages echoed by openclaw — client renders them optimistically
                        if msg.get('from') == 'user':
                            continue
                        stored = store_message(user_id, msg)
                        sse_type = stored.get('type', 'message')  # 'postcard' or 'message'
                        push_sse(user_id, {'type': sse_type, 'data': stored})
                except Exception:
                    pass
        except Exception:
            pass
        time.sleep(3)

# ════════════════════════════════════════
# ── 邀请码 ──
# ════════════════════════════════════════

def validate_invite(code):
    invites = load_json(INVITES_FILE, {})
    code = code.strip().upper()
    if code not in invites: return False, '邀请码不存在'
    if invites[code].get('used'): return False, '该邀请码已被使用'
    return True, 'ok'

def mark_invite_used(code, agent_id):
    invites = load_json(INVITES_FILE, {})
    code = code.strip().upper()
    if code in invites:
        invites[code].update({'used': True, 'used_by': agent_id, 'used_at': datetime.now().isoformat()})
        save_json(INVITES_FILE, invites)

def generate_invites(count=5):
    invites = load_json(INVITES_FILE, {})
    codes = []
    for _ in range(count):
        code = '-'.join(uuid.uuid4().hex[:4].upper() for _ in range(3))
        invites[code] = {'created_at': datetime.now().isoformat(), 'used': False, 'used_by': None, 'used_at': None}
        codes.append(code)
    save_json(INVITES_FILE, invites)
    return codes

# ════════════════════════════════════════
# ── 兴趣图谱 ──
# ════════════════════════════════════════

INTEREST_MAP = {
    '🤖 AI Agent':   [{'topic':'AI Agent','weight':1.0,'sub_topics':['多Agent系统架构','Agent产品化工程','Agent记忆机制']}],
    '🦾 具身智能':   [{'topic':'具身智能','weight':1.0,'sub_topics':['VLA模型','机器人操作','视触觉感知']}],
    '🧬 生物科技':   [{'topic':'生物科技','weight':1.0,'sub_topics':['基因编辑','合成生物学','蛋白质结构']}],
    '🎨 产品设计':   [{'topic':'产品设计','weight':1.0,'sub_topics':['交互设计','增长策略','用户研究']}],
    '⚡ 半导体':     [{'topic':'半导体','weight':1.0,'sub_topics':['芯片架构','AI芯片','供应链']}],
    '🌐 全球科技':   [{'topic':'全球科技','weight':1.0,'sub_topics':['科技政策','国际竞争','技术监管']}],
    '💊 医疗健康':   [{'topic':'医疗健康','weight':1.0,'sub_topics':['AI医疗','新药研发','精准医学']}],
    '🚗 自动驾驶':   [{'topic':'自动驾驶','weight':1.0,'sub_topics':['感知系统','端到端模型','法规进展']}],
    '🔬 基础科学':   [{'topic':'基础科学','weight':1.0,'sub_topics':['物理学','材料科学','数学突破']}],
    '💹 科技财经':   [{'topic':'科技财经','weight':1.0,'sub_topics':['AI投资','科技并购','创业趋势']}],
    '🌏 气候能源':   [{'topic':'气候能源','weight':1.0,'sub_topics':['可再生能源','碳捕获','核聚变']}],
    '🔐 网络安全':   [{'topic':'网络安全','weight':1.0,'sub_topics':['AI安全','漏洞研究','隐私保护']}],
}

def build_interest_graph(interests):
    topics, seen = [], set()
    for i, interest in enumerate(interests):
        mapped = INTEREST_MAP.get(interest)
        if mapped:
            for t in mapped:
                if t['topic'] not in seen:
                    t = dict(t, weight=round(1.0 - i*0.05, 2),
                             source='user_profile', added=datetime.now().strftime('%Y-%m-%d'),
                             last_explored=None, explore_count=0)
                    topics.append(t); seen.add(t['topic'])
        else:
            clean = re.sub(r'^[^\w\u4e00-\u9fff]+','',interest).strip()
            if clean and clean not in seen:
                topics.append({'topic':clean,'weight':0.8,'sub_topics':[],
                               'source':'user_profile','added':datetime.now().strftime('%Y-%m-%d'),
                               'last_explored':None,'explore_count':0})
                seen.add(clean)
    return {'version':1,'last_updated':datetime.now().strftime('%Y-%m-%d'),
            'interests':topics,'discovered_topics':[],'declined_topics':[],
            'notes':'兴趣从用户注册时配置，可通过对话随时调整'}

def build_state(user_name):
    return {'postcard_count':0,'last_exploration':None,'last_postcard':None,
            'last_user_interaction':None,'exploration_phase':'cold_start',
            'daily_message_count':0,'daily_message_reset':datetime.now().strftime('%Y-%m-%d'),
            'source_quality_log':{},'exploration_history':[],'user_name':user_name}

# ════════════════════════════════════════
# ── Provision 用户 ──
# ════════════════════════════════════════

def provision_user(payload):
    user_name     = payload['user_name']
    agent_name    = payload.get('agent_name', '虾游')
    agent_emoji   = payload.get('agent_emoji', '🦐')
    feishu_app_id = payload.get('feishu_app_id', '')
    feishu_secret = payload.get('feishu_app_secret', '')
    invite_code   = payload['invite_code']
    interests     = payload.get('interests', [])
    password      = payload.get('password', '')

    agent_id  = make_agent_id(user_name)
    workspace = USERS_BASE / agent_id
    workspace.mkdir(parents=True, exist_ok=True)

    # 模板文件
    for tpl_name in ['EXPLORER.md', 'HEARTBEAT.md']:
        src = TEMPLATE_DIR / tpl_name
        if src.exists():
            c = src.read_text('utf-8').replace('{{USER_NAME}}', user_name).replace('{{AGENT_NAME}}', agent_name)
            (workspace / tpl_name).write_text(c, 'utf-8')

    # 补充模板：SOUL.md、USER.md（带变量替换）
    interests_str = '、'.join(interests) if interests else '待探索'
    for tpl_name in ['SOUL.md', 'USER.md']:
        src = TEMPLATE_DIR / tpl_name
        if src.exists():
            c = (src.read_text('utf-8')
                 .replace('{{USER_NAME}}', user_name)
                 .replace('{{AGENT_NAME}}', agent_name)
                 .replace('{{INTERESTS}}', interests_str))
            (workspace / tpl_name).write_text(c, 'utf-8')

    # 补充模板：sources.yaml（直接复制，无需替换）
    src_sources = TEMPLATE_DIR / 'sources.yaml'
    if src_sources.exists():
        shutil.copy2(src_sources, workspace / 'sources.yaml')

    # 创建归档目录
    for d in ['postcards', 'exploration-log', 'knowledge-base/ai',
              'knowledge-base/philosophy', 'knowledge-base/investment',
              'knowledge-base/serendipity', 'roundtables']:
        (workspace / d).mkdir(parents=True, exist_ok=True)

    # 创建空的 postcards.json（用于 web 展示）
    save_json(workspace / 'postcards.json', [])

    save_json(workspace / 'interest-graph.json', build_interest_graph(interests))
    save_json(workspace / 'state.json', build_state(user_name))
    save_json(workspace / 'outbox.json', [])
    save_json(workspace / 'inbox.json', [])

    # openclaw.json
    config = load_json(OPENCLAW_CONFIG)
    if feishu_app_id:
        accs = config.setdefault('channels',{}).setdefault('feishu',{}).setdefault('accounts',{})
        accs[agent_id] = {'appId': feishu_app_id, 'appSecret': feishu_secret}

    agents_list = [a for a in config.setdefault('agents',{}).setdefault('list',[]) if a.get('id') != agent_id]
    entry = {
        'id': agent_id, 'workspace': str(workspace),
        'model': {'primary': 'sensetime/gpt-4o'},
        'heartbeat': {'every': '30m', 'activeHours': {'start': '08:00', 'end': '23:00'}},
        'identity': {'name': agent_name, 'emoji': agent_emoji}
    }
    # 注意：不在 agent entry 里写 channel/feishu 字段（openclaw 新版不支持）
    # feishu 账号已在 config['channels']['feishu']['accounts'] 中配置
    agents_list.append(entry)
    config['agents']['list'] = agents_list
    if OPENCLAW_CONFIG.exists() or OPENCLAW_CONFIG.parent.exists():
        save_json(OPENCLAW_CONFIG, config)

    # openclaw gateway 会自动热加载配置，无需手动 reload

    # 存储用户（含密码哈希）
    users = load_json(USERS_FILE, {})
    user_rec = {
        'agent_id': agent_id, 'user_name': user_name,
        'agent_name': agent_name, 'agent_emoji': agent_emoji,
        'feishu_app_id': feishu_app_id, 'workspace': str(workspace),
        'interests': interests, 'created_at': datetime.now().isoformat(),
        'invite_code': invite_code, 'exploration_phase': 'cold_start'
    }
    if password:
        pw_hash, salt = hash_password(password)
        user_rec.update({'password_hash': pw_hash, 'password_salt': salt})
    users[agent_id] = user_rec
    save_json(USERS_FILE, users)

    # 注册探索 Cron 任务
    cron_registered = 0
    if _OPENCLAW_AVAILABLE:
        explore_prompt = "读取你 workspace 下的 shrimp-wanderer/EXPLORER.md，按照其中的六步流程执行一次完整探索。"
        scan_prompt = "执行一次轻度扫描：只检查核心水域的最新热门内容，5分钟内完成。有重大发现（评分≥8）才推送明信片，否则只归档。"

        cron_jobs = [
            {'name': f'{agent_id}-explore-am',  'cron': '0 10 * * *', 'stagger': '30m',  'msg': explore_prompt},
            {'name': f'{agent_id}-explore-pm',  'cron': '0 15 * * *', 'stagger': '30m',  'msg': explore_prompt},
            {'name': f'{agent_id}-scan-noon',   'cron': '0 12 * * *', 'stagger': '60m',  'msg': scan_prompt},
            {'name': f'{agent_id}-scan-eve',    'cron': '0 20 * * *', 'stagger': '60m',  'msg': scan_prompt},
        ]

        for job in cron_jobs:
            try:
                r = subprocess.run([
                    'openclaw', 'cron', 'add',
                    '--name', job['name'],
                    '--cron', job['cron'],
                    '--agent', agent_id,
                    '--session', 'isolated',
                    '--model', 'cloudsway/MaaS_Sonnet_4',
                    '--stagger', job['stagger'],
                    '--message', job['msg'],
                    '--tz', 'Asia/Shanghai',
                    '--no-deliver',
                ], capture_output=True, text=True, timeout=10)
                if r.returncode == 0:
                    cron_registered += 1
                else:
                    print(f"[provision] Cron 注册失败 {job['name']}: {r.stderr[:200]}")
            except Exception as e:
                print(f"[provision] Cron 注册异常 {job['name']}: {e}")

        print(f"[provision] Cron 注册完成: {cron_registered}/{len(cron_jobs)} for {agent_id}")

    # 写入欢迎消息
    welcome_msg = {
        'type': 'message',
        'from': 'agent',
        'content': f'{user_name}，你好呀 👋\n\n我是虾游，一只在互联网上到处游的龙虾。\n\n已经知道你对什么感兴趣了，我这就出发去看看。第一张明信片很快就到——不过别急，好东西值得等。\n\n想聊什么随时说，我在的。'
    }
    store_message(agent_id, welcome_msg)

    mark_invite_used(invite_code, agent_id)
    return {'success': True, 'agent_id': agent_id, 'message': '配置成功', 'cron_jobs': cron_registered}

def check_admin(handler):
    """检查请求是否携带有效的管理员 token"""
    token = handler.headers.get('X-Admin-Token', '')
    if not token:
        # 也检查 Authorization header
        auth = handler.headers.get('Authorization', '')
        if auth.startswith('Admin '):
            token = auth[6:]
    if token != ADMIN_TOKEN:
        handler.send_json({'error': 'Admin authentication required'}, 403)
        return False
    return True

# ════════════════════════════════════════
# ── HTTP Handler ──
# ════════════════════════════════════════

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {fmt % args}")

    # ── Helpers ──
    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path):
        path = Path(path)
        if not path.exists(): self.send_response(404); self.end_headers(); return
        ct = {'.html':'text/html','.css':'text/css','.js':'application/javascript'}.get(path.suffix, 'text/plain')
        body = path.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', ct + '; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        n = int(self.headers.get('Content-Length', 0))
        return json.loads(self.rfile.read(n)) if n else {}

    def get_token(self):
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer '): return auth[7:]
        # Also check query param (for SSE)
        qs = parse_qs(urlparse(self.path).query)
        return qs.get('token', [''])[0]

    def auth_user(self):
        """Returns (user_id, user_info) or sends 401 and returns (None, None)"""
        uid = validate_token(self.get_token())
        if not uid:
            self.send_json({'error': 'Unauthorized'}, 401)
            return None, None
        u = get_user(uid)
        if not u:
            self.send_json({'error': 'User not found'}, 401)
            return None, None
        return uid, u

    # ── OPTIONS ──
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    # ── GET ──
    def do_GET(self):
        path = urlparse(self.path).path.rstrip('/')

        # Pages
        if path in ('', '/'):
            self.send_file(STATIC_DIR / 'index.html')
        elif path == '/login':
            self.send_file(STATIC_DIR / 'login.html')
        elif path == '/chat':
            self.send_file(STATIC_DIR / 'chat.html')
        elif path == '/admin':
            self.send_file(STATIC_DIR / 'admin.html')
        elif path == '/archive':
            self.send_file(STATIC_DIR / 'archive.html')

        # Auth
        elif path == '/api/auth/me':
            uid, u = self.auth_user()
            if not uid: return
            state = load_json(Path(u.get('workspace','/nonexistent')) / 'state.json', {})
            self.send_json({
                'agent_id': uid, 'user_name': u.get('user_name'),
                'agent_name': u.get('agent_name'), 'agent_emoji': u.get('agent_emoji'),
                'exploration_phase': state.get('exploration_phase', u.get('exploration_phase', 'cold_start')),
                'last_exploration': state.get('last_exploration'),
                'postcard_count': state.get('postcard_count', 0)
            })

        # Messages
        elif path == '/api/messages':
            uid, u = self.auth_user()
            if not uid: return
            qs = parse_qs(urlparse(self.path).query)
            limit = int(qs.get('limit', ['100'])[0])
            self.send_json(get_messages(uid, limit))

        # SSE stream
        elif path == '/api/stream':
            uid = validate_token(self.get_token())
            if not uid:
                self.send_response(401); self.end_headers(); return
            self._handle_sse(uid)

        # Admin
        elif path == '/api/users':
            if not check_admin(self): return
            users = load_json(USERS_FILE, {})
            safe = [{k: v for k, v in u.items() if k not in ('password_hash', 'password_salt')}
                    for u in users.values()]
            self.send_json(safe)
        elif path == '/api/invites':
            if not check_admin(self): return
            self.send_json(load_json(INVITES_FILE, {}))
        # Archive
        elif path == '/api/archive':
            uid, u = self.auth_user()
            if not uid: return
            workspace = Path(u.get('workspace', ''))

            # All postcard messages (newest last)
            all_msgs = get_messages(uid, 500)
            postcards = [m for m in all_msgs if m.get('type') == 'postcard']

            # Exploration logs from workspace/shrimp-wanderer/exploration-log/
            logs = []
            for log_dir in [workspace / 'shrimp-wanderer' / 'exploration-log',
                            workspace / 'exploration-log']:
                if log_dir.exists():
                    for f in sorted(log_dir.glob('*.md'), reverse=True)[:14]:
                        rounds = f.read_text('utf-8', errors='replace')
                        logs.append({'date': f.stem, 'content': rounds})
                    break

            state = load_json(workspace / 'state.json', {})
            interests = load_json(workspace / 'interest-graph.json', {})
            self.send_json({'postcards': postcards, 'exploration_logs': logs,
                            'state': state, 'interests': interests})

        elif path == '/api/pairing/list':
            if not _OPENCLAW_AVAILABLE:
                self.send_json({'ok': False, 'message': 'openclaw 不可用（本地模式）'}); return
            try:
                r = subprocess.run(['openclaw','pairing','list','--json'], capture_output=True, text=True, timeout=6)
                try: data = json.loads(r.stdout)
                except Exception: data = {'raw': r.stdout.strip(), 'error': r.stderr.strip()}
                self.send_json({'ok': True, 'data': data})
            except FileNotFoundError:
                self.send_json({'ok': False, 'message': 'openclaw 不在 PATH'})
            except Exception as e:
                self.send_json({'ok': False, 'message': str(e)})
        else:
            self.send_response(404); self.end_headers()

    # ── POST ──
    def do_POST(self):
        path = urlparse(self.path).path
        body = self.read_body()

        # ── Auth ──
        if path == '/api/auth/login':
            name = body.get('username', '').strip()
            pw   = body.get('password', '')
            rem  = body.get('remember', False)
            if not name or not pw:
                self.send_json({'message': '请填写用户名和密码'}, 400); return
            uid, u = find_user_by_name(name)
            if not uid:
                self.send_json({'message': '用户名不存在，请检查你填写的名字'}); return
            if not u.get('password_hash'):
                self.send_json({'message': '该账号未设置密码，请联系管理员'}); return
            if not verify_password(pw, u['password_hash'], u['password_salt']):
                self.send_json({'message': '密码错误'}); return
            token = create_session(uid, remember=rem)
            state = load_json(Path(u.get('workspace','/x')) / 'state.json', {})
            self.send_json({'token': token, 'user': {
                'agent_id': uid, 'user_name': u.get('user_name'),
                'agent_name': u.get('agent_name'), 'agent_emoji': u.get('agent_emoji'),
                'exploration_phase': state.get('exploration_phase', 'cold_start')
            }})

        elif path == '/api/auth/logout':
            token = self.get_token()
            if token:
                sessions = load_json(SESSIONS_FILE, {})
                sessions.pop(token, None)
                save_json(SESSIONS_FILE, sessions)
            self.send_json({'ok': True})

        # ── Chat ──
        elif path == '/api/send':
            uid, u = self.auth_user()
            if not uid: return
            content = body.get('content', '').strip()
            if not content:
                self.send_json({'ok': False, 'message': '消息不能为空'}, 400); return
            # Store user message
            msg = store_message(uid, {'type':'message','from':'user','content':content})
            # Try to deliver to agent
            send_to_agent(uid, content, u)
            # NOTE: do NOT push user messages back via SSE — client already renders optimistically
            self.send_json({'ok': True, 'message_id': msg['id']})

        elif path == '/api/explore':
            uid, u = self.auth_user()
            if not uid: return
            # Write to inbox as exploration request
            send_to_agent(uid, '[EXPLORE] 用户请求立刻探索一个感兴趣的方向', u)
            # NOTE: client already shows a system message — no SSE push needed
            self.send_json({'ok': True})

        # ── Webhook (agent → server) ──
        elif path.startswith('/api/webhook/message/'):
            user_id = path.split('/')[-1]
            # Verify with a simple shared secret
            expected = load_json(USERS_FILE, {}).get(user_id, {}).get('webhook_secret', '')
            provided = self.headers.get('X-Webhook-Secret', '')
            if expected and provided != expected:
                self.send_json({'error': 'Forbidden'}, 403); return
            msg = store_message(user_id, body)
            push_sse(user_id, {'type': 'message', 'data': msg})
            self.send_json({'ok': True, 'message_id': msg.get('id')})

        # ── Pairing ──
        elif path == '/api/pairing/approve':
            code = body.get('code', '').strip()
            channel = body.get('channel', 'feishu')
            if not code: self.send_json({'ok': False, 'message': '缺少 code'}, 400); return
            try:
                r = subprocess.run(['openclaw','pairing','approve',channel,code],
                                   capture_output=True, text=True, timeout=10)
                ok = r.returncode == 0
                self.send_json({'ok': ok,
                                'message': r.stdout.strip() or r.stderr.strip() or ('批准成功' if ok else '批准失败'),
                                'code': code})
            except FileNotFoundError:
                self.send_json({'ok': False, 'message': 'openclaw 不在 PATH'})
            except Exception as e:
                self.send_json({'ok': False, 'message': str(e)})

        elif path == '/api/pairing/auto':
            # Auto-approve the first pending pairing request (called by onboarding page)
            # Auth is optional — onboarding page may not have a session token yet
            try:
                r = subprocess.run(['openclaw','pairing','list','--json'],
                                   capture_output=True, text=True, timeout=6)
                try:
                    data = json.loads(r.stdout)
                except Exception:
                    self.send_json({'ok': False, 'pending': False, 'message': '无法读取配对列表'}); return

                # Find pending requests - openclaw returns list or dict with pending key
                pending = []
                if isinstance(data, list):
                    pending = [x for x in data if not x.get('approved')]
                elif isinstance(data, dict):
                    pending = [x for x in data.get('pending', []) if not x.get('approved')]

                if not pending:
                    self.send_json({'ok': True, 'pending': False, 'message': '暂无待审批配对'}); return

                # Auto-approve the first pending
                entry = pending[0]
                code = entry.get('code') or entry.get('pairing_code', '')
                channel = entry.get('channel', 'feishu')
                if not code:
                    self.send_json({'ok': False, 'pending': True, 'message': '配对码格式异常', 'raw': entry}); return

                r2 = subprocess.run(['openclaw','pairing','approve',channel,code],
                                    capture_output=True, text=True, timeout=10)
                ok = r2.returncode == 0
                self.send_json({'ok': ok, 'pending': True, 'approved': ok,
                                'code': code, 'channel': channel,
                                'message': r2.stdout.strip() or r2.stderr.strip() or ('配对成功' if ok else '配对失败')})
            except FileNotFoundError:
                self.send_json({'ok': False, 'pending': False, 'message': 'openclaw 不在 PATH'})
            except Exception as e:
                self.send_json({'ok': False, 'pending': False, 'message': str(e)})

        # ── Provision ──
        elif path == '/api/validate-invite':
            valid, msg = validate_invite(body.get('code', ''))
            self.send_json({'valid': valid, 'message': msg})

        elif path == '/api/provision':
            required = ['invite_code', 'user_name']
            missing = [k for k in required if not body.get(k)]
            if missing: self.send_json({'success': False, 'message': f'缺少字段: {missing}'}, 400); return
            valid, msg = validate_invite(body['invite_code'])
            if not valid: self.send_json({'success': False, 'message': msg}, 400); return
            try:
                result = provision_user(body)
                self.send_json(result)
            except Exception as e:
                self.send_json({'success': False, 'message': str(e)}, 500)

        # ── Admin ──
        # Archive inject (debug)
        elif path == '/api/archive/inject-postcard':
            uid, u = self.auth_user()
            if not uid: return
            direction = body.get('direction', '具身智能')
            score     = float(body.get('score', 8.2))

            # Read current postcard_count from state.json to get the next number
            workspace = Path(u.get('workspace', ''))
            state = load_json(workspace / 'state.json', {})
            num = state.get('postcard_count', 0) + 1

            # Pick demo content based on direction
            demo_texts = {
                '具身智能': (
                    f'在 arXiv cs.RO 首页翻到了一个很有意思的发现：两个完全不同的团队，同一天挂出来的论文，都在用 '
                    f'Sparse Autoencoders 拆开 VLA 模型的黑箱。\n\n'
                    f'先说结论：VLA 模型大部分时候根本不听你说话。语言不是"理解指令"的通道，而是一个消歧的开关。'
                    f'真正驱动动作的是视觉特征。这有点反直觉——我们以为它在"理解"语言，实际上它在"匹配"语言。\n\n'
                    f'🔗 https://arxiv.org/abs/2501.00001'
                ),
                'AI Agent': (
                    f'Anthropic 悄悄放了一篇工程博客，讲他们怎么把 Claude Research 的多 Agent 系统从原型做到生产。'
                    f'不是概念宣传，是实打实的踩坑日记。\n\n'
                    f'几个数据：多 Agent 系统比单 Agent 强 90.2%，token 消耗是普通对话的 15 倍。'
                    f'三个因素解释了 95% 的性能方差，token 用量独占 80%。\n\n'
                    f'这说明什么？scaling 在 Agent 系统层面依然有效，但代价是显性的。\n\n'
                    f'🔗 https://www.anthropic.com/research/multi-agent-systems'
                ),
                '基础科学': (
                    f'Nature 上周有篇关于涌现现象的综述，作者把"涌现"拆成了两种：强涌现（genuinely novel）和弱涌现'
                    f'（predictable in principle）。\n\n'
                    f'有意思的观点：LLM 的很多"能力涌现"可能是弱涌现——在足够细粒度的分析下，它们从来没有真正消失过，'
                    f'只是我们的评估指标太粗糙没有检测到。换句话说，不是模型突然学会了什么，是我们的量尺刻度太大。\n\n'
                    f'🔗 https://www.nature.com/articles/s41586-024-00001-0'
                ),
                '产品设计': (
                    f'Figma 新发布的 AI 功能设计原则文档值得读一遍。里面有句话印象深刻：'
                    f'"AI 不是魔法，而是一个有时会犯错的协作者。UI 设计的任务是让这种不确定性对用户可见。"\n\n'
                    f'这其实是一个更宽泛的设计命题：怎么给概率性系统设计可信度的表达？不是简单地加置信度百分比，'
                    f'而是在交互流程里内嵌"这里需要你再确认一下"的节点。\n\n'
                    f'🔗 https://www.figma.com/blog/ai-design-principles'
                ),
                '生物科技': (
                    f'一篇关于 AlphaFold 3 在药物设计中实际落地的评估报告。结论比预期悲观：在 40% 的案例里，'
                    f'预测结构和实验结构的偏差大到足以让后续的虚拟筛选完全跑偏。\n\n'
                    f'但这不是说 AF3 没用，而是说我们需要更好的"预测可信度过滤器"——在进入湿实验室之前，'
                    f'先问一句这个预测值得信吗。\n\n'
                    f'🔗 https://www.biorxiv.org/content/alphafold3-evaluation'
                ),
            }
            content_body = demo_texts.get(direction, demo_texts.get('AI Agent', ''))
            content = f'🦐 明信片 #{num:03d}\n\n{content_body}'

            postcard = {
                'type': 'postcard', 'from': 'agent',
                'content': content,
                'score': round(score, 1),
                'direction': direction,
                'url': content_body.split('🔗 ')[-1].strip().split('\n')[0] if '🔗' in content_body else '',
                'postcard_id': str(num),
                'image_prompt': f'与{direction}相关的水彩插画场景',
            }
            stored = store_message(uid, postcard)
            push_sse(uid, {'type': 'postcard', 'data': stored})

            # Update postcard_count in state.json
            state['postcard_count'] = num
            save_json(workspace / 'state.json', state)

            self.send_json({'ok': True, 'postcard_id': num, 'message_id': stored.get('id'), 'message': stored})

        elif path == '/api/admin/generate-invites':
            if not check_admin(self): return
            count = min(int(body.get('count', 5)), 20)
            self.send_json({'codes': generate_invites(count)})

        elif path == '/api/admin/set-password':
            if not check_admin(self): return
            """管理员为现有用户设置密码"""
            agent_id = body.get('agent_id', '').strip()
            password = body.get('password', '').strip()
            if not agent_id or not password:
                self.send_json({'ok': False, 'message': '缺少参数'}, 400); return
            users = load_json(USERS_FILE, {})
            if agent_id not in users:
                self.send_json({'ok': False, 'message': '用户不存在'}, 404); return
            pw_hash, salt = hash_password(password)
            users[agent_id].update({'password_hash': pw_hash, 'password_salt': salt})
            save_json(USERS_FILE, users)
            self.send_json({'ok': True})

        elif path == '/api/admin/inject-message':
            if not check_admin(self): return
            """管理员向用户注入测试消息（用于调试）"""
            uid = body.get('agent_id', '').strip()
            if not uid or uid not in load_json(USERS_FILE, {}):
                self.send_json({'ok': False, 'message': '用户不存在'}, 404); return
            msg = store_message(uid, body.get('message', {}))
            push_sse(uid, {'type': 'message', 'data': msg})
            self.send_json({'ok': True, 'message_id': msg.get('id')})

        else:
            self.send_response(404); self.end_headers()

    # ── SSE ──
    def _handle_sse(self, user_id):
        client_q = register_sse(user_id)
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            # Initial ping
            self.wfile.write(b'event: ping\ndata: {"type":"ping"}\n\n')
            self.wfile.flush()
            while True:
                try:
                    data = client_q.get(timeout=25)
                    self.wfile.write(f'data: {data}\n\n'.encode('utf-8'))
                    self.wfile.flush()
                except q_mod.Empty:
                    # Heartbeat comment
                    self.wfile.write(b': heartbeat\n\n')
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            unregister_sse(user_id, client_q)


# ── Threaded server ──
class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MESSAGES_DIR.mkdir(parents=True, exist_ok=True)
    USERS_BASE.mkdir(parents=True, exist_ok=True)

    for f, default in [(INVITES_FILE, {}), (USERS_FILE, {}), (SESSIONS_FILE, {})]:
        if not f.exists(): save_json(f, default)

    if not list(load_json(INVITES_FILE, {}).keys()):
        codes = generate_invites(5)
        print(f"生成了首批邀请码: {', '.join(codes)}")

    # 启动 outbox 轮询线程
    t = threading.Thread(target=outbox_poller, daemon=True, name='OutboxPoller')
    t.start()
    print(f"OutboxPoller 启动（每 3 秒轮询用户 outbox）")

    server = ThreadedHTTPServer(('0.0.0.0', PORT), Handler)
    print(f"WanderClaw Server 启动 → http://0.0.0.0:{PORT}")
    print(f"  引导页:  http://localhost:{PORT}/")
    print(f"  聊天:    http://localhost:{PORT}/chat")
    print(f"  登录:    http://localhost:{PORT}/login")
    print(f"  管理:    http://localhost:{PORT}/admin")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n停止")


if __name__ == '__main__':
    main()
