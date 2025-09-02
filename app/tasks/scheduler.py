from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.schedulers.background import BackgroundScheduler

# 创建 APScheduler 实例
from init.settings import REDIS_HOST, REDIS_PORT, REDIS_DATABASE, REDIS_PWD


scheduler = BackgroundScheduler(
    jobstores={'default': RedisJobStore(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DATABASE, password=REDIS_PWD)},
    executors={'default': ThreadPoolExecutor(3)},
    job_defaults={'coalesce': True}
)