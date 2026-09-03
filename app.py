from flask import Flask, render_template, request, jsonify, session, Response, stream_with_context
from flask_cors import CORS
import hashlib
import json
import os
from datetime import datetime, timedelta
import uuid
import logging

from agent.react_agent import ReactAgent

# ---------- 配置 ----------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production-123456'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# 允许跨域（如果需要）
CORS(app, supports_credentials=True)

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------- 数据管理 ----------
USER_DB_FILE = "user_data/users.json"
SESSION_DATA_DIR = "session_data"


def ensure_directories():
    """确保必要的目录存在"""
    os.makedirs(os.path.dirname(USER_DB_FILE), exist_ok=True)
    os.makedirs(SESSION_DATA_DIR, exist_ok=True)


def load_users():
    """加载用户数据"""
    if os.path.exists(USER_DB_FILE):
        try:
            with open(USER_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    return {}


def save_users(users):
    """保存用户数据"""
    ensure_directories()
    with open(USER_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def hash_password(password: str) -> str:
    """密码哈希"""
    return hashlib.md5(password.encode()).hexdigest()


def get_user_sessions_file(username: str) -> str:
    """获取用户会话文件路径"""
    return os.path.join(SESSION_DATA_DIR, f"sessions_{username}.json")


def load_sessions(username: str) -> list:
    """加载用户的所有会话"""
    file_path = get_user_sessions_file(username)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []


def save_sessions(username: str, sessions: list):
    """保存用户的所有会话"""
    ensure_directories()
    file_path = get_user_sessions_file(username)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)


def get_session_title(messages: list) -> str:
    """生成会话标题"""
    for msg in messages:
        if msg.get("role") == "user":
            text = msg.get("content", "")
            if len(text) > 20:
                return text[:20] + "..."
            return text
    return "新会话"


# ---------- 路由 ----------
@app.route('/')
def index():
    """主页"""
    if session.get('logged_in'):
        return render_template('chat.html', username=session.get('username'))
    return render_template('login.html')


# ---------- 认证API ----------
@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    remember = data.get('remember', False)

    if not username or not password:
        return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400

    users = load_users()
    if username in users and users[username]['password'] == hash_password(password):
        session.clear()
        session['username'] = username
        session['logged_in'] = True
        session.permanent = remember

        logger.info(f"用户 {username} 登录成功")
        return jsonify({
            'success': True,
            'data': {
                'username': username,
                'login_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        })

    logger.warning(f"用户 {username} 登录失败")
    return jsonify({'success': False, 'error': '用户名或密码错误'}), 401


@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    data = request.json
    username = data.get('username', '').strip()
    password = data.get('password', '')
    confirm_password = data.get('confirm_password', '')

    if not username or not password:
        return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400

    if len(username) < 2:
        return jsonify({'success': False, 'error': '用户名至少2位'}), 400

    if len(password) < 6:
        return jsonify({'success': False, 'error': '密码长度至少6位'}), 400

    if password != confirm_password:
        return jsonify({'success': False, 'error': '两次输入的密码不一致'}), 400

    users = load_users()
    if username in users:
        return jsonify({'success': False, 'error': '用户名已存在'}), 400

    users[username] = {
        'password': hash_password(password),
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_users(users)

    logger.info(f"新用户注册: {username}")
    return jsonify({'success': True, 'message': '注册成功'})


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """退出登录"""
    username = session.get('username')
    session.clear()
    logger.info(f"用户 {username} 退出登录")
    return jsonify({'success': True})


@app.route('/api/auth/check', methods=['GET'])
def check_auth():
    """检查登录状态"""
    if session.get('logged_in'):
        return jsonify({
            'logged_in': True,
            'username': session.get('username')
        })
    return jsonify({'logged_in': False})


# ---------- 会话API ----------
@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """获取所有会话"""
    if not session.get('logged_in'):
        return jsonify({'error': '未登录'}), 401

    username = session.get('username')
    sessions = load_sessions(username)
    return jsonify({'sessions': sessions})


@app.route('/api/sessions', methods=['POST'])
def create_session():
    """创建新会话"""
    if not session.get('logged_in'):
        return jsonify({'error': '未登录'}), 401

    username = session.get('username')
    messages = request.json.get('messages', [])

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

    return jsonify({'session': new_session})


@app.route('/api/sessions/<session_id>', methods=['PUT'])
def update_session(session_id):
    """更新会话"""
    if not session.get('logged_in'):
        return jsonify({'error': '未登录'}), 401

    username = session.get('username')
    data = request.json
    messages = data.get('messages')
    title = data.get('title')

    sessions = load_sessions(username)
    for s in sessions:
        if s['id'] == session_id:
            if messages is not None:
                s['messages'] = messages
                # 自动更新标题
                if messages and not title:
                    s['title'] = get_session_title(messages)
            if title:
                s['title'] = title
            break
    save_sessions(username, sessions)

    return jsonify({'success': True})


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """删除会话"""
    if not session.get('logged_in'):
        return jsonify({'error': '未登录'}), 401

    username = session.get('username')
    sessions = load_sessions(username)
    sessions = [s for s in sessions if s['id'] != session_id]
    save_sessions(username, sessions)

    return jsonify({'success': True})


# ---------- 聊天API ----------
@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """流式聊天"""
    if not session.get('logged_in'):
        return jsonify({'error': '未登录'}), 401

    username = session.get('username')
    data = request.json
    prompt = data.get('prompt', '').strip()
    session_id = data.get('session_id')

    if not prompt:
        return jsonify({'error': '问题不能为空'}), 400

    @stream_with_context
    def generate():
        full_response = ""
        try:
            agent = ReactAgent(user_id=username)

            # 流式输出
            for chunk in agent.execute_stream(prompt):
                if chunk:
                    full_response += chunk
                    yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"

            # 保存消息到会话
            if session_id:
                sessions = load_sessions(username)
                for s in sessions:
                    if s['id'] == session_id:
                        # 添加用户消息
                        s['messages'].append({'role': 'user', 'content': prompt})
                        # 添加助手回复
                        s['messages'].append({'role': 'assistant', 'content': full_response})
                        # 如果只有两条消息，更新标题
                        if len(s['messages']) == 2:
                            s['title'] = get_session_title(s['messages'])
                        break
                save_sessions(username, sessions)

            yield f"data: {json.dumps({'content': '', 'done': True, 'full_response': full_response})}\n\n"

        except Exception as e:
            logger.error(f"聊天错误: {str(e)}", exc_info=True)
            error_msg = f"❌ 发生错误: {str(e)}"
            yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"

    return Response(generate(), mimetype='text/event-stream')


# ---------- 错误处理 ----------
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': '接口不存在'}), 404


@app.errorhandler(500)
def internal_error(e):
    logger.error(f"服务器错误: {str(e)}")
    return jsonify({'error': '服务器内部错误'}), 500


# ---------- 启动 ----------
if __name__ == '__main__':
    ensure_directories()
    app.run(
        debug=False,
        host='0.0.0.0',
        port=5000,
        threaded=True
    )