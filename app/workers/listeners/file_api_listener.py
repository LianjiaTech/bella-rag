from app.workers.handlers.file_api_task import file_api_task_callback
from app.workers.listeners.base import BaseListener
from init.settings import KAFKA

file_api_task_config = {
    "bootstrap_servers": KAFKA.get("FILE_API_TASK_BOOTSTRAP_SERVERS", None),
    "group_id": KAFKA.get("FILE_API_TASK_GROUP_ID", None),
    "topic": KAFKA.get("FILE_API_TASK_TOPIC", None),
    "callback": file_api_task_callback,
    "callback_timeout": 50,  # 执行超时时间（秒）
    'max.poll.interval.ms': 60000,  # 60s,避免_MAX_POLL_EXCEEDED
}


class FileApiTaskListener(BaseListener):

    def __init__(self, instance_num):
        super().__init__(instance_num, **file_api_task_config)
