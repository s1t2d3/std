from celery_task.crawl_task import crawl_cctv
from celery_task.crawl_task import crawl_pengpai


res1 = crawl_cctv.delay()
res2 = crawl_pengpai.delay()
print(res1, res2)  # uuid
