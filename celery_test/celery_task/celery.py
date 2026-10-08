from celery import Celery
from celery.schedules import crontab
import logging

app = Celery(
    'celery',
    broker='redis://127.0.0.1:6379/0',
    backend='redis://127.0.0.1:6379/0',
    include=[
        'celery_task.crawl_task',
    ],
)

# ---------- 基础配置 ----------
app.conf.timezone = 'Asia/Shanghai'
app.conf.enable_utc = False
app.conf.broker_connection_retry_on_startup = True

# ---------- 日志配置：解决重复输出 / DEBUG 被标 WARNING ----------
app.conf.worker_hijack_root_logger = False   # 不让 Celery 接管 root logger
app.conf.worker_loglevel = 'INFO'            # worker 默认 INFO，别开 DEBUG

# ---------- 定时任务 ----------
# 如果你要“每 4 小时”跑一次，把下面 */12 改成 */4
app.conf.beat_schedule = {
    'schedule_crawl_pengpai': {
        'task': 'celery_task.crawl_task.crawl_pengpai',
        'schedule': crontab(hour='*/4', minute=0),      # 0:00 4:00 8:00 ...
    },
    'schedule_crawl_cctv': {
        'task': 'celery_task.crawl_task.crawl_cctv',
        'schedule': crontab(hour='*/4', minute=1),      # 0:01 4:01 8:01 ...
    },
    # 'schedule_load_vector': {
    #     'task': 'celery_task.vector_task.load_news_to_vector',
    #     'schedule': crontab(hour='*/4', minute=5),     # 留足 30 分钟给爬虫
    #     # 如果你的爬虫很快，可以改回 minute=5
    # },
}