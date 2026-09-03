// static/js/app.js - 修复版

'use strict';

// ============================================
// 全局状态
// ============================================
const state = {
    loggedIn: true,
    username: document.getElementById('username')?.textContent || '',
    sessions: [],
    currentSessionId: null,
    messages: [],
    isLoading: false,
    streamingContent: '',
};

const API_BASE = '/api';

// ============================================
// DOM 引用（添加空值检查）
// ============================================
const DOM = {
    loginPage: document.querySelector('.login-page'),
    loginForm: document.getElementById('loginForm'),
    registerForm: document.getElementById('registerForm'),
    loginError: document.getElementById('loginError'),
    registerError: document.getElementById('registerError'),
    registerSuccess: document.getElementById('registerSuccess'),
    tabs: document.querySelectorAll('.tab'),

    // 聊天页
    messagesContainer: document.getElementById('messagesContainer'),
    sessionList: document.getElementById('sessionList'),
    promptInput: document.getElementById('promptInput'),
    sendBtn: document.getElementById('sendBtn'),
    newSessionBtn: document.getElementById('newSessionBtn'),
    clearAllBtn: document.getElementById('clearAllBtn'),
    logoutBtn: document.getElementById('logoutBtn'),
    usernameDisplay: document.getElementById('username'),
};

// ============================================
// 工具函数
// ============================================
function scrollToBottom() {
    if (DOM.messagesContainer) {
        DOM.messagesContainer.scrollTop = DOM.messagesContainer.scrollHeight;
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function log(msg, data) {
    console.log(`🔍 [DEBUG] ${msg}`, data || '');
}

function error(msg, data) {
    console.error(`❌ [ERROR] ${msg}`, data || '');
}

// ============================================
// 认证相关（仅当元素存在时才绑定）
// ============================================
if (DOM.tabs && DOM.tabs.length > 0) {
    DOM.tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            DOM.tabs.forEach(t => t.classList.remove('active'));
            this.classList.add('active');

            const tabName = this.dataset.tab;
            if (tabName === 'login') {
                if (DOM.loginForm) DOM.loginForm.classList.add('active');
                if (DOM.registerForm) DOM.registerForm.classList.remove('active');
                if (DOM.loginError) DOM.loginError.classList.remove('show');
                if (DOM.registerError) DOM.registerError.classList.remove('show');
                if (DOM.registerSuccess) DOM.registerSuccess.classList.remove('show');
            } else {
                if (DOM.loginForm) DOM.loginForm.classList.remove('active');
                if (DOM.registerForm) DOM.registerForm.classList.add('active');
                if (DOM.loginError) DOM.loginError.classList.remove('show');
                if (DOM.registerError) DOM.registerError.classList.remove('show');
                if (DOM.registerSuccess) DOM.registerSuccess.classList.remove('show');
            }
        });
    });
}

// 登录
if (DOM.loginForm) {
    DOM.loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const username = document.getElementById('loginUsername')?.value.trim() || '';
        const password = document.getElementById('loginPassword')?.value || '';
        const remember = document.getElementById('rememberMe')?.checked || false;

        if (DOM.loginError) DOM.loginError.classList.remove('show');

        if (!username || !password) {
            if (DOM.loginError) {
                DOM.loginError.textContent = '❌ 用户名和密码不能为空';
                DOM.loginError.classList.add('show');
            }
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ username, password, remember })
            });
            const data = await res.json();

            if (data.success) {
                window.location.href = '/';
            } else {
                if (DOM.loginError) {
                    DOM.loginError.textContent = '❌ ' + (data.error || '登录失败');
                    DOM.loginError.classList.add('show');
                }
            }
        } catch (e) {
            if (DOM.loginError) {
                DOM.loginError.textContent = '❌ 网络错误，请重试';
                DOM.loginError.classList.add('show');
            }
        }
    });
}

// 注册
if (DOM.registerForm) {
    DOM.registerForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const username = document.getElementById('registerUsername')?.value.trim() || '';
        const password = document.getElementById('registerPassword')?.value || '';
        const confirmPassword = document.getElementById('registerConfirm')?.value || '';

        if (DOM.registerError) DOM.registerError.classList.remove('show');
        if (DOM.registerSuccess) DOM.registerSuccess.classList.remove('show');

        if (!username || !password) {
            if (DOM.registerError) {
                DOM.registerError.textContent = '❌ 用户名和密码不能为空';
                DOM.registerError.classList.add('show');
            }
            return;
        }
        if (password.length < 6) {
            if (DOM.registerError) {
                DOM.registerError.textContent = '❌ 密码长度至少6位';
                DOM.registerError.classList.add('show');
            }
            return;
        }
        if (password !== confirmPassword) {
            if (DOM.registerError) {
                DOM.registerError.textContent = '❌ 两次输入的密码不一致';
                DOM.registerError.classList.add('show');
            }
            return;
        }

        try {
            const res = await fetch(`${API_BASE}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password, confirm_password: confirmPassword })
            });
            const data = await res.json();

            if (data.success) {
                if (DOM.registerSuccess) {
                    DOM.registerSuccess.textContent = '✅ 注册成功！请登录';
                    DOM.registerSuccess.classList.add('show');
                }
                document.getElementById('registerUsername').value = '';
                document.getElementById('registerPassword').value = '';
                document.getElementById('registerConfirm').value = '';

                setTimeout(() => {
                    DOM.tabs.forEach(t => t.classList.remove('active'));
                    document.querySelector('[data-tab="login"]')?.classList.add('active');
                    if (DOM.registerForm) DOM.registerForm.classList.remove('active');
                    if (DOM.loginForm) DOM.loginForm.classList.add('active');
                    document.getElementById('loginUsername').value = username;
                }, 1000);
            } else {
                if (DOM.registerError) {
                    DOM.registerError.textContent = '❌ ' + (data.error || '注册失败');
                    DOM.registerError.classList.add('show');
                }
            }
        } catch (e) {
            if (DOM.registerError) {
                DOM.registerError.textContent = '❌ 网络错误，请重试';
                DOM.registerError.classList.add('show');
            }
        }
    });
}

// ============================================
// 会话管理
// ============================================
async function loadSessions() {
    try {
        log('加载会话列表...');
        const res = await fetch(`${API_BASE}/sessions`, { credentials: 'include' });
        const data = await res.json();
        state.sessions = data.sessions || [];
        log('会话加载完成:', state.sessions.length);
        renderSessionList();
    } catch (e) {
        error('加载会话失败:', e);
    }
}

function renderSessionList() {
    const list = DOM.sessionList;
    if (!list) return;

    if (state.sessions.length === 0) {
        list.innerHTML = '<div class="empty">暂无会话</div>';
        return;
    }

    list.innerHTML = state.sessions.map(s => `
        <div class="session-item ${state.currentSessionId === s.id ? 'active' : ''}" data-id="${s.id}">
            <span class="session-title">${escapeHtml(s.title)}</span>
            <button class="btn-delete" data-id="${s.id}">✕</button>
        </div>
    `).join('');

    // 事件绑定
    list.querySelectorAll('.session-item').forEach(item => {
        item.addEventListener('click', function(e) {
            if (e.target.classList.contains('btn-delete')) return;
            const id = this.dataset.id;
            loadSession(id);
        });
    });

    list.querySelectorAll('.btn-delete').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const id = this.dataset.id;
            deleteSession(id);
        });
    });
}

function loadSession(sessionId) {
    const session = state.sessions.find(s => s.id === sessionId);
    if (!session) return;

    log('加载会话:', sessionId);
    state.currentSessionId = sessionId;
    state.messages = session.messages || [];
    renderMessages();
    renderSessionList();
}

async function deleteSession(sessionId) {
    try {
        await fetch(`${API_BASE}/sessions/${sessionId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        state.sessions = state.sessions.filter(s => s.id !== sessionId);
        if (state.currentSessionId === sessionId) {
            state.currentSessionId = state.sessions.length > 0 ? state.sessions[0].id : null;
            state.messages = state.currentSessionId
                ? state.sessions.find(s => s.id === state.currentSessionId)?.messages || []
                : [];
            renderMessages();
        }
        renderSessionList();
    } catch (e) {
        error('删除会话失败:', e);
    }
}

async function createNewSession() {
    log('创建新会话');
    state.currentSessionId = null;
    state.messages = [];
    state.streamingContent = '';
    renderMessages();
    renderSessionList();
}

async function clearAllSessions() {
    if (!confirm('确定要清空所有会话吗？')) return;
    for (const s of state.sessions) {
        await deleteSession(s.id);
    }
    state.sessions = [];
    state.currentSessionId = null;
    state.messages = [];
    renderMessages();
    renderSessionList();
}

// ============================================
// 消息渲染
// ============================================
function renderMessages() {
    const container = DOM.messagesContainer;
    if (!container) return;

    if (state.messages.length === 0 && !state.streamingContent) {
        container.innerHTML = `
            <div class="welcome">
                <h2>👋 欢迎使用智能新闻助手</h2>
                <p>我可以帮你：</p>
                <p>📰 获取今日新闻摘要<br>
                🔍 搜索特定新闻资讯<br>
                📅 查询指定日期的新闻<br>
                🤔 回答新闻相关问题</p>
                <p class="hint">在下方输入框开始提问吧 👇</p>
            </div>
        `;
        return;
    }

    let html = state.messages.map(msg => `
        <div class="message ${msg.role}">
            <div class="message-content">${escapeHtml(msg.content)}</div>
        </div>
    `).join('');

    if (state.streamingContent) {
        html += `
            <div class="message assistant">
                <div class="message-content">${escapeHtml(state.streamingContent)}<span class="cursor">▌</span></div>
            </div>
        `;
    }

    if (state.isLoading && !state.streamingContent) {
        html += `
            <div class="message assistant">
                <div class="message-content thinking">🤔 正在思考中...</div>
            </div>
        `;
    }

    container.innerHTML = html;
    scrollToBottom();
}

// ============================================
// ⭐ 核心：发送消息（放在前面，确保定义）
// ============================================
async function sendMessage() {
    log('📤 sendMessage 被调用');

    if (!DOM.promptInput) {
        error('promptInput 不存在');
        return;
    }

    const prompt = DOM.promptInput.value.trim();
    log('输入内容:', prompt);

    if (!prompt || state.isLoading) {
        log('忽略: 空输入或正在加载');
        return;
    }

    // 清空输入
    DOM.promptInput.value = '';

    // 添加用户消息
    state.messages.push({ role: 'user', content: prompt });
    state.isLoading = true;
    state.streamingContent = '';
    renderMessages();
    log('用户消息已添加');

    // 如果没有会话，先创建
    if (!state.currentSessionId) {
        log('创建新会话...');
        try {
            const res = await fetch(`${API_BASE}/sessions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ messages: [{ role: 'user', content: prompt }] })
            });
            const data = await res.json();
            if (data.session) {
                state.currentSessionId = data.session.id;
                state.sessions.unshift(data.session);
                renderSessionList();
                log('会话创建成功:', state.currentSessionId);
            }
        } catch (e) {
            error('创建会话失败:', e);
            state.isLoading = false;
            renderMessages();
            return;
        }
    }

    // 发送消息到API
    try {
        log('发送消息到API...');
        const response = await fetch(`${API_BASE}/chat/stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({
                prompt,
                session_id: state.currentSessionId
            })
        });

        log('API响应状态:', response.status);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullResponse = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.content) {
                            fullResponse += data.content;
                            state.streamingContent = fullResponse;
                            renderMessages();
                        }
                        if (data.done) {
                            if (data.full_response) {
                                fullResponse = data.full_response;
                            }
                            state.streamingContent = '';
                            state.messages.push({ role: 'assistant', content: fullResponse });
                            state.isLoading = false;
                            renderMessages();
                            log('消息完成');
                            await loadSessions();  // 刷新会话列表更新标题
                        }
                    } catch (parseError) {
                        // 忽略解析错误
                    }
                }
            }
        }
    } catch (e) {
        error('发送消息失败:', e);
        state.messages.push({ role: 'assistant', content: '❌ 发生错误: ' + e.message });
        state.isLoading = false;
        state.streamingContent = '';
        renderMessages();
    }
}

// ============================================
// 退出登录
// ============================================
async function logout() {
    log('退出登录');
    try {
        await fetch(`${API_BASE}/auth/logout`, {
            method: 'POST',
            credentials: 'include'
        });
    } catch (e) {}
    window.location.href = '/';
}

// ============================================
// ⭐ 初始化（放在最后，确保所有函数都已定义）
// ============================================
async function init() {
    log('🚀 初始化开始...');

    // 检查是否在聊天页面
    if (!document.querySelector('.app')) {
        log('不在聊天页面，跳过初始化');
        return;
    }

    // 检查登录状态
    try {
        log('检查登录状态...');
        const res = await fetch(`${API_BASE}/auth/check`, { credentials: 'include' });
        const data = await res.json();
        log('登录状态:', data);

        if (!data.logged_in) {
            log('未登录，跳转到登录页');
            window.location.href = '/';
            return;
        }

        state.username = data.username;
        if (DOM.usernameDisplay) {
            DOM.usernameDisplay.textContent = data.username;
        }
    } catch (e) {
        error('检查登录状态失败:', e);
        window.location.href = '/';
        return;
    }

    // 检查关键DOM元素
    const requiredElements = ['sendBtn', 'promptInput', 'messagesContainer', 'sessionList'];
    let allFound = true;
    for (const id of requiredElements) {
        if (!DOM[id]) {
            error(`❌ 关键元素 #${id} 不存在`);
            allFound = false;
        } else {
            log(`✅ #${id} 存在`);
        }
    }

    if (!allFound) {
        error('❌ 关键DOM元素缺失，请检查HTML模板');
        return;
    }

    // 加载会话
    log('加载会话...');
    await loadSessions();

    // 如果有会话，加载第一个
    if (state.sessions.length > 0) {
        loadSession(state.sessions[0].id);
    }

    // ⭐ 绑定事件（确保所有元素都存在）
    log('绑定事件...');

    // 发送按钮
    if (DOM.sendBtn) {
        // 移除旧监听器（避免重复绑定）
        DOM.sendBtn.removeEventListener('click', sendMessage);
        DOM.sendBtn.addEventListener('click', function(e) {
            log('🖱️ 点击发送按钮');
            sendMessage();
        });
        log('✅ sendBtn 事件绑定完成');
    }

    // 输入框回车
    if (DOM.promptInput) {
        DOM.promptInput.removeEventListener('keydown', handleKeydown);
        DOM.promptInput.addEventListener('keydown', handleKeydown);
        log('✅ promptInput 事件绑定完成');
    }

    // 新建会话
    if (DOM.newSessionBtn) {
        DOM.newSessionBtn.removeEventListener('click', createNewSession);
        DOM.newSessionBtn.addEventListener('click', function() {
            log('🖱️ 点击新建会话');
            createNewSession();
        });
        log('✅ newSessionBtn 事件绑定完成');
    }

    // 清空所有会话
    if (DOM.clearAllBtn) {
        DOM.clearAllBtn.removeEventListener('click', clearAllSessions);
        DOM.clearAllBtn.addEventListener('click', function() {
            log('🖱️ 点击清空所有会话');
            clearAllSessions();
        });
        log('✅ clearAllBtn 事件绑定完成');
    }

    // 退出登录
    if (DOM.logoutBtn) {
        DOM.logoutBtn.removeEventListener('click', logout);
        DOM.logoutBtn.addEventListener('click', function() {
            log('🖱️ 点击退出登录');
            logout();
        });
        log('✅ logoutBtn 事件绑定完成');
    }

    log('✅ 初始化完成！');
}

// 回车事件处理函数
function handleKeydown(e) {
    if (e.key === 'Enter') {
        log('⌨️ 按下回车键');
        e.preventDefault();
        sendMessage();
    }
}

// ============================================
// 启动
// ============================================
// 将关键函数暴露到全局（方便调试）
window.sendMessage = sendMessage;
window.createNewSession = createNewSession;
window.logout = logout;
window.loadSessions = loadSessions;
window.init = init;

// 等待DOM加载完成
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    // DOM已经加载，直接初始化
    init();
}

log('📦 app.js 加载完成');