import streamlit as st
from streamlit import session_state
import hashlib
import json
import os
from datetime import datetime, timedelta
import uuid

from agent.react_agent import ReactAgent

# ---------- 页面配置 ----------
st.set_page_config(
    page_title="智能新闻助手",
    page_icon="🤖",
    layout="wide"
)

# ---------- 用户管理 ----------
USER_DB_FILE = "user_data/users.json"


def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_users(users):
    with open(USER_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def hash_password(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()


# ---------- 会话管理 ----------
# ---------- 会话管理 ----------
SESSION_DATA_DIR = "session_data"

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

def update_session(username: str, session_id: str, messages: list, title: str = None):
    """更新会话"""
    sessions = load_sessions(username)
    for s in sessions:
        if s["id"] == session_id:
            s["messages"] = messages
            if title:
                s["title"] = title
            break
    save_sessions(username, sessions)

def save_sessions(username: str, sessions: list):
    """保存用户的所有会话"""
    file_path = get_user_sessions_file(username)
    os.makedirs(SESSION_DATA_DIR, exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)

def delete_session(username: str, session_id: str):
    """删除指定会话"""
    sessions = load_sessions(username)
    sessions = [s for s in sessions if s["id"] != session_id]
    save_sessions(username, sessions)


def get_session_title(messages: list) -> str:
    for msg in messages:
        if msg["role"] == "user":
            text = msg["content"][:20]
            return text + "..." if len(msg["content"]) > 20 else text
    return "新会话"


# ---------- 登录持久化（使用 localStorage） ----------
def get_login_from_localstorage():
    """
    从 localStorage 获取登录信息
    通过 JavaScript 写入 session_state
    """
    # 检查 URL 参数中是否有登录信息（由 JS 注入）
    if "login_restore" in st.query_params:
        try:
            login_json = st.query_params["login_restore"]
            login_data = json.loads(login_json)

            # 检查是否过期
            expire_time = login_data.get("expire")
            if expire_time:
                expire = datetime.strptime(expire_time, "%Y-%m-%d %H:%M:%S")
                if datetime.now() > expire:
                    st.query_params.clear()
                    return None

            # 清除 URL 参数，防止刷新时重复
            st.query_params.clear()
            return login_data
        except:
            st.query_params.clear()
            return None
    return None


def inject_login_restore_script():
    js_code = """
    <script>
    (function() {
        try {
            if (window.location.search.includes('login_restore')) {
                return;
            }
            const loginData = localStorage.getItem('news_agent_login');
            if (loginData) {
                const encoded = encodeURIComponent(loginData);
                const url = new URL(window.location.href);
                url.searchParams.set('login_restore', encoded);
                window.location.replace(url.toString());
            }
        } catch(e) {
            console.error('恢复登录失败:', e);
        }
    })();
    </script>
    """
    st.html(js_code)  # st.html 可以执行 JavaScript


def set_login_cookie(username: str):
    """保存登录信息到 localStorage"""
    login_data = {
        "username": username,
        "login_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "expire": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
    }

    # 通过 JavaScript 写入 localStorage
    js_code = f"""
    <script>
    try {{
        localStorage.setItem('news_agent_login', '{json.dumps(login_data)}');
        console.log('✅ 登录信息已保存');
    }} catch(e) {{
        console.error('保存登录失败:', e);
    }}
    </script>
    """
    st.html(js_code)  # st.html 可以执行 JavaScript


def clear_login_cookie():
    """清除 localStorage 中的登录信息"""
    js_code = """
    <script>
    try {
        localStorage.removeItem('news_agent_login');
        console.log('✅ 登录信息已清除');
    } catch(e) {
        console.error('清除登录失败:', e);
    }
    </script>
    """
    st.html(js_code)  # st.html 可以执行 JavaScript


# ---------- 登录页面 ----------
def login_page():
    """登录页面"""
    # 尝试从 localStorage 恢复登录
    login_data = get_login_from_localstorage()
    if login_data:
        session_state["logged_in"] = True
        session_state["username"] = login_data["username"]
        session_state["login_time"] = login_data.get("login_time", "")
        st.rerun()
        return

    st.title("🤖 智能新闻助手")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        tab1, tab2 = st.tabs(["🔐 登录", "📝 注册"])

        with tab1:
            with st.form(key="login_form"):
                username = st.text_input("用户名", placeholder="请输入用户名")
                password = st.text_input("密码", type="password", placeholder="请输入密码")
                remember_me = st.checkbox("记住我（7天内免登录）", value=True)
                login_btn = st.form_submit_button("登录", use_container_width=True)

                if login_btn:
                    if not username or not password:
                        st.error("❌ 用户名和密码不能为空")
                    else:
                        users = load_users()
                        if username in users and users[username]["password"] == hash_password(password):
                            session_state["logged_in"] = True
                            session_state["username"] = username
                            session_state["login_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                            if remember_me:
                                set_login_cookie(username)

                            st.success(f"✅ 欢迎回来，{username}！")
                            st.rerun()
                        else:
                            st.error("❌ 用户名或密码错误")

        with tab2:
            with st.form(key="register_form"):
                new_username = st.text_input("用户名", placeholder="请输入用户名")
                new_password = st.text_input("密码", type="password", placeholder="请输入密码（至少6位）")
                confirm_password = st.text_input("确认密码", type="password", placeholder="再次输入密码")
                register_btn = st.form_submit_button("注册", use_container_width=True)

                if register_btn:
                    if not new_username or not new_password:
                        st.error("❌ 用户名和密码不能为空")
                    elif len(new_password) < 6:
                        st.error("❌ 密码长度至少6位")
                    elif new_password != confirm_password:
                        st.error("❌ 两次输入的密码不一致")
                    else:
                        users = load_users()
                        if new_username in users:
                            st.error("❌ 用户名已存在")
                        else:
                            users[new_username] = {
                                "password": hash_password(new_password),
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                            save_users(users)
                            st.success("✅ 注册成功！请登录")
                            st.rerun()


# ---------- 退出登录 ----------
def logout():
    clear_login_cookie()
    session_state["logged_in"] = False
    session_state["username"] = None
    session_state.pop("current_session_id", None)
    session_state["messages"] = []
    st.rerun()


# ---------- 侧边栏 ----------
def render_sidebar():
    with st.sidebar:
        st.title("💬 会话列表")
        st.markdown("---")

        username = session_state.get("username", "游客")
        st.write(f"👤 {username}")

        if st.button("➕ 新建会话", use_container_width=True):
            session_state["messages"] = []
            session_state["current_session_id"] = None
            st.rerun()

        st.markdown("---")

        sessions = load_sessions(username)
        if not sessions:
            st.caption("暂无会话，发送消息后自动创建")
        else:
            for s in sessions:
                col1, col2 = st.columns([4, 1])
                with col1:
                    is_current = s["id"] == session_state.get("current_session_id")
                    label = f"📌 {s['title']}" if is_current else s["title"]
                    if st.button(label, key=f"session_{s['id']}", use_container_width=True):
                        session_state["current_session_id"] = s["id"]
                        session_state["messages"] = s.get("messages", [])
                        st.rerun()
                with col2:
                    if st.button("✕", key=f"del_{s['id']}"):
                        delete_session(username, s["id"])
                        if session_state.get("current_session_id") == s["id"]:
                            session_state["current_session_id"] = None
                            session_state["messages"] = []
                        st.rerun()

        st.markdown("---")

        if st.button("🗑️ 清空所有会话", use_container_width=True):
            sessions = []
            save_sessions(username, sessions)
            session_state["current_session_id"] = None
            session_state["messages"] = []
            st.rerun()

        st.markdown("---")
        st.caption("💡 点击会话切换，点击 ✕ 删除")

        if st.button("🚪 退出登录", use_container_width=True):
            logout()


# ---------- 主应用 ----------
def main_app():
    username = session_state.get("username", "default_user")

    render_sidebar()

    st.title("🤖 智能新闻助手")
    st.divider()

    if not session_state["messages"]:
        st.markdown("""
        <div style="text-align: center; padding: 60px 20px; color: #666;">
            <h2 style="font-size: 32px; margin-bottom: 20px;">👋 欢迎使用智能新闻助手</h2>
            <p style="font-size: 18px; margin-bottom: 10px;">我可以帮你：</p>
            <p style="font-size: 16px; line-height: 2;">
                📰 获取今日新闻摘要<br>
                🔍 搜索特定新闻资讯<br>
                📅 查询指定日期的新闻<br>
                🤔 回答新闻相关问题
            </p>
            <p style="font-size: 16px; color: #999; margin-top: 30px;">
                在下方输入框开始提问吧 👇
            </p>
        </div>
        """, unsafe_allow_html=True)

        if "agent" not in session_state:
            session_state["agent"] = ReactAgent(user_id=username)

        prompt = st.chat_input("请输入问题...")

        if prompt:
            st.chat_message("user").write(prompt)
            session_state["messages"].append({"role": "user", "content": prompt})

            sessions = load_sessions(username)
            new_id = str(uuid.uuid4())[:8]
            sessions.append({
                "id": new_id,
                "title": get_session_title(session_state["messages"]),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "messages": session_state["messages"].copy()
            })
            save_sessions(username, sessions)
            session_state["current_session_id"] = new_id

            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""

                with st.spinner("🤔 正在思考中..."):
                    try:
                        res_stream = session_state["agent"].execute_stream(prompt)

                        for chunk in res_stream:
                            if chunk:
                                full_response += chunk
                                response_placeholder.markdown(full_response + "▌")

                        if full_response:
                            response_placeholder.markdown(full_response)
                        else:
                            error_msg = "⚠️ 抱歉，我暂时无法回答这个问题。"
                            response_placeholder.markdown(error_msg)
                            full_response = error_msg

                    except Exception as e:
                        error_msg = f"❌ 发生错误: {str(e)}"
                        response_placeholder.markdown(error_msg)
                        full_response = error_msg

            if full_response:
                session_state["messages"].append({
                    "role": "assistant",
                    "content": full_response
                })

            update_session(username, new_id, session_state["messages"])
            st.rerun()

        return

    if "agent" not in session_state:
        session_state["agent"] = ReactAgent(user_id=username)

    for message in session_state["messages"]:
        st.chat_message(message["role"]).write(message["content"])

    prompt = st.chat_input("请输入问题...")

    if prompt:
        st.chat_message("user").write(prompt)
        session_state["messages"].append({"role": "user", "content": prompt})

        current_id = session_state.get("current_session_id")
        if current_id:
            sessions = load_sessions(username)
            for s in sessions:
                if s["id"] == current_id:
                    if len(s["messages"]) == 0:
                        s["title"] = get_session_title(session_state["messages"])
                    break
            save_sessions(username, sessions)

        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""

            with st.spinner("🤔 正在思考中..."):
                try:
                    res_stream = session_state["agent"].execute_stream(prompt)

                    for chunk in res_stream:
                        if chunk:
                            full_response += chunk
                            response_placeholder.markdown(full_response + "▌")

                    if full_response:
                        response_placeholder.markdown(full_response)
                    else:
                        error_msg = "⚠️ 抱歉，我暂时无法回答这个问题。"
                        response_placeholder.markdown(error_msg)
                        full_response = error_msg

                except Exception as e:
                    error_msg = f"❌ 发生错误: {str(e)}"
                    response_placeholder.markdown(error_msg)
                    full_response = error_msg

        if full_response:
            session_state["messages"].append({
                "role": "assistant",
                "content": full_response
            })

        if current_id:
            update_session(username, current_id, session_state["messages"])

        st.rerun()


# ---------- 主流程 ----------
if __name__ == "__main__":
    if "logged_in" not in session_state:
        session_state["logged_in"] = False

    if "username" not in session_state:
        session_state["username"] = None

    if "messages" not in session_state:
        session_state["messages"] = []

    # 注入恢复脚本（仅在未登录时执行）
    if not session_state.get("logged_in"):
        inject_login_restore_script()

    if session_state.get("logged_in"):
        main_app()
    else:
        login_page()