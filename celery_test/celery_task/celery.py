from celery import Celery
from datetime import timedelta
from celery.schedules import crontab
app = Celery(
    'celery',
    broker='redis://127.0.0.1:6379/0',
    backend='redis://127.0.0.1:6379/0',
    include = ['celery_task.crawl_task']
)
# 配置时区
app.conf.timezone = 'Asia/Shanghai'
app.conf.enable_utc = False
# 配置定时任务
app.conf.beat_schedule = {
    'schedule_crawl_pengpai': {
        'task': 'celery_task.crawl_task.crawl_pengpai',
        'schedule': crontab(hour='*/4'),# 每隔4个小时执行
    },
    'schedule_crawl_cctv': {
        'task': 'celery_task.crawl_task.crawl_cctv',
        'schedule': crontab(hour='*/4', minute=1),# 每隔4个小时1分钟执行
    },
    'schedule_load_vector': {
        'task': 'celery_task.vector_task.load_news_to_vector',
        'schedule': crontab(hour='*/4', minute=5),  # 0:05,4:05,8:05...
        # 在采集任务完成后 5 分钟执行
    },
}

app.conf.broker_connection_retry_on_startup = True