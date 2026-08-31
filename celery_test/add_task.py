from celery_task.crawl_task import crawl_baidu
from celery_task.crawl_task import crawl_cctv


res1 = crawl_baidu.delay()
res2 = crawl_cctv.delay()
print(res1,res2)#uuid