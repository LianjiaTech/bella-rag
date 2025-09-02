import atexit

from apscheduler.triggers.cron import CronTrigger

from app.tasks.data_clear_task import clear_deleted_qas_task
from app.tasks.scheduler import scheduler


def start_schedulers():
    scheduler.add_job(clear_deleted_qas_task,
                      trigger=CronTrigger(hour=0, minute=0),  # 每天零点执行
                      id='clear_deleted_qas_task',
                      replace_existing=True)
    scheduler.start()
    # 优雅关闭
    atexit.register(lambda: scheduler.shutdown())