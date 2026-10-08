import sys
import os
from celery import Task
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# 添加项目根目录到 Python 路径
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from .celery import app


def _run_spider(spider_name: str):
    """
    在独立子进程中运行 Scrapy 爬虫，避免 Twisted reactor 无法重启的问题。
    这样即使 worker 复用进程，也不会报 ReactorNotRestartable。
    """
    import subprocess
    cmd = [sys.executable, '-m', 'scrapy', 'crawl', spider_name]
    # 假设 scrapy.cfg 在项目根目录
    result = subprocess.run(
        cmd,
        cwd=root_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"spider {spider_name} failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result.stdout


@app.task(bind=True, max_retries=2, default_retry_delay=60)
def crawl_cctv(self):
    """运行央视 Scrapy 爬虫"""
    print("-" * 20)
    print("开始爬取央视新闻 (Scrapy)")
    try:
        _run_spider('cctv')
        print("央视爬虫执行完毕")
        return {"status": "success", "spider": "cctv"}
    except Exception as e:
        print(f"央视爬虫失败: {e}")
        # 可选：失败重试
        # raise self.retry(exc=e)
        return {"status": "failed", "spider": "cctv", "error": str(e)}


@app.task(bind=True, max_retries=2, default_retry_delay=60)
def crawl_pengpai(self):
    """运行澎湃 Scrapy 爬虫"""
    print("-" * 20)
    print("开始爬取澎湃新闻 (Scrapy)")
    try:
        _run_spider('pengpai')
        print("澎湃爬虫执行完毕")
        return {"status": "success", "spider": "pengpai"}
    except Exception as e:
        print(f"澎湃爬虫失败: {e}")
        return {"status": "failed", "spider": "pengpai", "error": str(e)}