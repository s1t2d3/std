import sys
import os
import subprocess
import json
import asyncio



# 添加项目根目录到 Python 路径，这样才能导入 pengpai_new
# 当前文件: D:\develop\PycharmProjects\网爬\celery_test\celery_task\crawl_task.py
# 项目根目录: D:\develop\PycharmProjects\网爬
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from pengpai_new.pengpai import get_pengpai_news
from cctv_new.cctv_new import get_all_news_async

from .celery import app

@app.task
def crawl_pengpai():
    print("-" * 20)
    print("开始爬取澎湃新闻")
    get_pengpai_news()
    print("-" * 20)
    print("爬取澎湃新闻成功")
    return 20


# ========================================
# 异步任务（央视） - 关键改动
# ========================================
@app.task
def crawl_cctv():
    """异步爬取央视新闻"""
    print("-" * 20)
    print("开始爬取央视新闻（异步）")
    try:
        # 直接 await 异步函数
        result = asyncio.run(get_all_news_async(max_concurrent=10))
        print("爬取成功")
        return {"status": "success", "data": result}
    except Exception as e:
        print(f"爬取失败: {e}")
        return {"status": "failed", "source": "cctv", "error": str(e)}


@app.task
def load_news_to_vector():
    """加载新闻到向量库"""
    from rag.vector_store import VectorStoreService
    vector_store = VectorStoreService()
    count = vector_store.load_news_from_directory()
    return {"status": "success", "count": count}