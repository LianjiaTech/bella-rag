from app.workers.handlers.knowledge_file_delete_task import knowledge_file_delete_callback
from app.workers.listeners.base import BaseListener
from app.workers.producers.producers import knowledge_file_delete_producer
from init.settings import KAFKA

knowledge_file_delete_listener_config = {
    "bootstrap_servers": KAFKA.get("KNOWLEDGE_FILE_DELETE_BOOTSTRAP_SERVERS", None),
    "group_id": KAFKA.get("KNOWLEDGE_FILE_DELETE_GROUP_ID", None),
    "topic": KAFKA.get("KNOWLEDGE_FILE_DELETE_TOPIC", None),
    "callback": knowledge_file_delete_callback,
    "callback_timeout": 7000,  # 执行超时时间（秒）
    "producer": knowledge_file_delete_producer, # 消息重试producer
    "max.poll.interval.ms": 7200000,  # 120分钟,避免_MAX_POLL_EXCEEDED
    "err_retry_max": 4,
}


class KnowledgeFileDeleteListener(BaseListener):

    def __init__(self, instance_num):
        super().__init__(instance_num, **knowledge_file_delete_listener_config)
