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

# ── 路径配置 ──
OPENCLAW_CONFIG = Path('/root/.openclaw/openclaw.json')
USERS_BASE      = Path('/root/wanderClaw/users')
TEMPLATE_DIR    = Path(__file__).parent / 'templates'
DATA_DIR        = Path(__file__).parent / 'data'
STATIC_DIR      = Path(__file__).parent
INVITES_FILE    = DATA_DIR / 'invites.json'
USERS_FILE      = DATA_DIR / 'users.json'
SESSIONS_FILE   = DATA_DIR / 'sessions.json'
MESSAGES_DIR    = DATA_DIR / 'messages'
PORT = 8080

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
    """写入 inbox.json，尝试触发 agent"""
    workspace = Path(user_info.get('workspace', ''))
    if not workspace.exists():
        return False
    inbox_f = workspace / 'inbox.json'
    inbox = load_json(inbox_f, [])
    inbox.append({'content': content, 'timestamp': datetime.now().isoformat(), 'read': False})
    save_json(inbox_f, inbox)

    # 尝试通过 openclaw CLI 触发 agent
    agent_id = user_info.get('agent_id', user_id)
    try:
        subprocess.Popen(
            ['openclaw', 'agent', 'notify', agent_id, '--inbox'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass
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
                        stored = store_message(user_id, msg)
                        push_sse(user_id, {'type': 'message', 'data': stored})
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

    # EXPLORER.md 模板
    src = TEMPLATE_DIR / 'EXPLORER.md'
    if src.exists():
        c = src.read_text('utf-8').replace('{{USER_NAME}}', user_name).replace('{{AGENT_NAME}}', agent_name)
        (workspace / 'EXPLORER.md').write_text(c, 'utf-8')

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
    if feishu_app_id:
        entry['channel'] = {'feishu': {'account': agent_id}}
    agents_list.append(entry)
    config['agents']['list'] = agents_list
    save_json(OPENCLAW_CONFIG, config)

    try: subprocess.run(['openclaw','reload'], timeout=10, check=False)
    except Exception: pass

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

    mark_invite_used(invite_code, agent_id)
    return {'success': True, 'agent_id': agent_id, 'message': '配置成功'}

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
            users = load_json(USERS_FILE, {})
            safe = [{k: v for k, v in u.items() if k not in ('password_hash', 'password_salt')}
                    for u in users.values()]
            self.send_json(safe)
        elif path == '/api/invites':
            self.send_json(load_json(INVITES_FILE, {}))
        elif path == '/api/pairing/list':
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
            # Push back to SSE (so other devices see it)
            push_sse(uid, {'type': 'message', 'data': msg})
            self.send_json({'ok': True, 'message_id': msg['id']})

        elif path == '/api/explore':
            uid, u = self.auth_user()
            if not uid: return
            # Write to inbox as exploration request
            send_to_agent(uid, '[EXPLORE] 用户请求立刻探索一个感兴趣的方向', u)
            # System message
            sys_msg = store_message(uid, {'type':'system','content':'已发送探索指令，虾游出发中 🔭'})
            push_sse(uid, {'type': 'message', 'data': sys_msg})
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
            uid, u = self.auth_user()
            if not uid: return
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
        elif path == '/api/admin/generate-invites':
            count = min(int(body.get('count', 5)), 20)
            self.send_json({'codes': generate_invites(count)})

        elif path == '/api/admin/set-password':
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
