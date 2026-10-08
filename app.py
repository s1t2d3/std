from flask import Flask, render_template, request, jsonify, session, Response, stream_with_context
from flask_cors import CORS
import hashlib
import json
import os
from datetime import datetime, timedelta
import uuid
import logging

from agent.react_agent import ReactAgent
from sql.sql_tools import SQLTools

# ---------- 配置 ----------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production-123456'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.json.ensure_ascii = False

CORS(app, supports_credentials=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- 数据管理 ----------
USER_DB_FILE = "user_data/users.json"
SESSION_DATA_DIR = "session_data"

# 创建数据库实例
db = SQLTools()


def ensure_directories():
    os.makedirs(os.path.dirname(USER_DB_FILE), exist_ok=True)
    os.makedirs(SESSION_DATA_DIR, exist_ok=True)


def load_users():
    if os.path.exists(USER_DB_FILE):
        try:
            with open(USER_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    return {}


def save_users(users):
    ensure_directories()
    with open(USER_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()


def get_user_sessions_file(username: str) -> str:
    return os.path.join(SESSION_DATA_DIR, f"sessions_{username}.json")


def load_sessions(username: str) -> list:
    file_path = get_user_sessions_file(username)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []


def save_sessions(username: str, sessions: list):
    ensure_directories()
    file_path = get_user_sessions_file(username)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)


def get_session_title(messages: list) -> str:
    for msg in messages:
        if msg.get("role") == "user":
            text = msg.get("content", "")
            if len(text) > 20:
                return text[:20] + "..."
            return text
    return "新会话"


# ---------- 统一响应工具 ----------
def resp(success: bool, msg: str, data=None, status: int = 200):
    """
    统一响应格式：
    {
        "success": true/false,
        "msg": "提示信息",
        "data": {...}   # 可选
    }
    """
    body = {"success": success, "msg": msg}
    if data is not None:
        body["data"] = data
    return jsonify(body), status


# ---------- 路由 ----------
@app.route('/')
def index():
    if session.get('logged_in'):
        return render_template('chat.html', username=session.get('username'))
    return render_template('login.html')


# ---------- 认证API ----------
@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    remember = data.get('remember', False)

    if not username or not password:
        return resp(False, "用户名和密码不能为空", status=400)

    users = load_users()
    if username in users and users[username]['password'] == hash_password(password):
        session.clear()
        session['username'] = username
        session['logged_in'] = True
        session.permanent = remember
        # session['token'] = str(uuid.uuid4())

        logger.info(f"用户 {username} 登录成功")
        return resp(True, "登录成功", {
            'username': username,
            'login_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            # "token": session.get('token')
        })

    logger.warning(f"用户 {username} 登录失败")
    return resp(False, "用户名或密码错误", status=401)


@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    if not username or not password:
        return resp(False, "用户名和密码不能为空", status=400)

    if len(username) < 2:
        return resp(False, "用户名至少2位", status=400)

    if len(password) < 6:
        return resp(False, "密码长度至少6位", status=400)

    if password != confirm_password:
        return resp(False, "两次输入的密码不一致", status=400)

    users = load_users()
    if username in users:
        return resp(False, "用户名已存在", status=400)

    users[username] = {
        'password': hash_password(password),
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_users(users)
    db.sql_add(username, password)
    logger.info(f"新用户注册: {username}")
    return resp(True, "注册成功")


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    username = session.get('username')
    session.clear()
    logger.info(f"用户 {username} 退出登录")
    return resp(True, "退出成功")


@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    if session.get('logged_in'):
        return resp(True, "已登录", {
            'logged_in': True,
            'username': session.get('username')
        })
    return resp(False, "未登录", {'logged_in': False})


# ---------- 会话API ----------
@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    if not session.get('logged_in'):
        return resp(False, "未登录", status=401)

    username = session.get('username')
    sessions = load_sessions(username)
    return resp(True, "获取会话列表成功", {'sessions': sessions})


@app.route('/api/sessions', methods=['POST'])
def create_session():
    if not session.get('logged_in'):
        return resp(False, "未登录", status=401)

    username = session.get('username')
    data = request.json or {}
    messages = data.get('messages', [])

    session_id = str(uuid.uuid4())[:8]
    title = get_session_title(messages) if messages else "新会话"

    new_session = {
        'id': session_id,
        'title': title,
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'messages': messages
    }

    sessions = load_sessions(username)
    sessions.append(new_session)
    save_sessions(username, sessions)

    return resp(True, "创建会话成功", {'session': new_session})


@app.route('/api/sessions/<session_id>', methods=['PUT'])
def update_session(session_id):
    if not session.get('logged_in'):
        return resp(False, "未登录", status=401)

    username = session.get('username')
    data = request.json or {}
    messages = data.get('messages')
    title = data.get('title')

    sessions = load_sessions(username)
    found = False
    for s in sessions:
        if s['id'] == session_id:
            found = True
            if messages is not None:
                s['messages'] = messages
                if messages and not title:
                    s['title'] = get_session_title(messages)
            if title:
                s['title'] = title
            break
    save_sessions(username, sessions)

    if not found:
        return resp(False, "会话不存在", status=404)
    return resp(True, "更新会话成功")


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    if not session.get('logged_in'):
        return resp(False, "未登录", status=401)

    username = session.get('username')
    sessions = load_sessions(username)
    before = len(sessions)
    sessions = [s for s in sessions if s['id'] != session_id]
    save_sessions(username, sessions)

    if len(sessions) == before:
        return resp(False, "会话不存在", status=404)
    return resp(True, "删除会话成功")


# ---------- 聊天API ----------
@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """流式聊天（SSE 中也带上 msg 字段）"""
    if not session.get('logged_in'):
        return resp(False, "未登录", status=401)

    username = session.get('username')
    data = request.json or {}
    prompt = data.get('prompt', '').strip()
    session_id = data.get('session_id')

    if not prompt:
        return resp(False, "问题不能为空", status=400)

    @stream_with_context
    def generate():
        full_response = ""
        try:
            agent = ReactAgent(user_id=username)

            # 流式输出：每个 chunk 都带 msg
            for chunk in agent.execute_stream(prompt):
                if chunk:
                    full_response += chunk
                    yield f"data: {json.dumps({'success': True, 'msg': chunk, 'content': chunk, 'done': False}, ensure_ascii=False)}\n\n"

            # 保存消息到会话
            if session_id:
                sessions = load_sessions(username)
                for s in sessions:
                    if s['id'] == session_id:
                        s['messages'].append({'role': 'user', 'content': prompt})
                        s['messages'].append({'role': 'assistant', 'content': full_response})
                        if len(s['messages']) == 2:
                            s['title'] = get_session_title(s['messages'])
                        break
                save_sessions(username, sessions)

            # 结束帧
            yield f"data: {json.dumps({'success': True, 'msg': '回复完成', 'content': '', 'done': True, 'full_response': full_response}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"聊天错误: {str(e)}")
            error_msg = f"发生错误: {str(e)}"
            yield f"data: {json.dumps({'success': False, 'msg': error_msg, 'content': error_msg, 'done': True, 'error': True}, ensure_ascii=False)}\n\n"

    return Response(generate(), mimetype='text/event-stream')


# ---------- 错误处理 ----------
@app.errorhandler(404)
def not_found(e):
    return resp(False, "接口不存在", status=404)


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"服务器错误: {str(e)}")
    return resp(False, "服务器内部错误", status=500)


# ---------- 启动 ----------
if __name__ == '__main__':
    ensure_directories()
    app.run(
        debug=False,
        host='0.0.0.0',
        port=5005,
        threaded=True
    )