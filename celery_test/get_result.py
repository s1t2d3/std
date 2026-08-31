from celery_task.celery import app
from celery.result import AsyncResult

id = '6431c343-30a3-425f-bfa6-13e71b73b91c'

if __name__ == "__main__":
    result = AsyncResult(id=id,app=app)
    if result.successful():
        result = result.get()
        print(result)
    elif result.failed():
        print("任务失败")
    elif result.status == "PENDING":
        print("任务等待执行")
    elif result.status == "RETRY":
        print("任务异常正在重试")
    else:
        print("任务正在被执行")