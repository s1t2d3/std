# 智能新闻助手 Agent

基于 LangChain 和 RAG 的智能新闻对话系统，定时抓取新闻，通过对话提供新闻摘要和问答。

![开发状态](https://img.shields.io/badge/status-developing-yellow)
![Python](https://img.shields.io/badge/python-3.8+-blue)

---

## 核心特性

- 定时抓取央视、澎湃等主流新闻
- RAG + ChromaDB 向量检索，基于本地新闻知识库问答
- LangChain 实现多轮智能对话
- Celery + Redis 异步处理耗时任务
- Flask 提供 Web 交互界面

---

## 技术栈

Python / LangChain / ChromaDB / aiohttp / requests / Celery / Redis / Flask

---

## 项目结构

```
std/
├── agent/              # Agent 核心逻辑
├── cctv_new/           # 央视新闻爬虫
├── pengpai_new/        # 澎湃新闻爬虫
├── celery_test/        # Celery 任务配置
├── chrom_db/           # 向量数据库
├── config/             # 配置文件
├── data/news/          # 新闻数据
├── logs/               # 日志
├── model/              # 数据模型
├── prompts/            # 提示词模板
├── rag/                # RAG 检索组件
├── static/             # 静态资源
├── templates/          # HTML 模板
├── utils/              # 工具函数
├── app.py              # 主入口
└── md5.txt             # 数据校验
└── requirements.txt    # 环境依赖
```

---

## 快速启动

```bash
# 1. 克隆
git clone https://github.com/s1t2d3/std.git
cd std

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动 Redis（需提前安装）
redis-server

# 4. 启动 Celery
cd celery_test
./start_celery.bat

# 5. 启动 Web（新的终端）
python app.py
```

访问 `http://127.0.0.1:5000`

---

## 使用示例

在对话框输入：
- “今天有什么AI新闻？”
- “总结今天最新的科技头条。”

---

## 未来计划

- [ ] 支持更多新闻源
- [ ] 新闻订阅与推送
- [ ] 优化检索性能
- [ ] 单元测试与 CI

---

## 许可证

待添加
