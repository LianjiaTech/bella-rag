from app.workers.handlers.knowledge_context_summary_task import knowledge_file_context_summary_callback
from app.workers.listeners.base import BaseListener
from app.workers.producers.producers import knowledge_file_extractor_producer
from init.settings import KAFKA

knowledge_file_context_task_listener_config = {
    "bootstrap_servers": KAFKA.get("KNOWLEDGE_FILE_INDEX_DONE_BOOTSTRAP_SERVERS", None),
    "group_id": KAFKA.get("KNOWLEDGE_FILE_CONTEXT_TASK_GROUP_ID", None),
    "topic": KAFKA.get("KNOWLEDGE_FILE_INDEX_DONE_TOPIC", None),
    "callback": knowledge_file_context_summary_callback,
    'callback_timeout': 1000,  # 执行超时时间（秒）
    "producer": knowledge_file_extractor_producer,  # 消息重试producer
    'max.poll.interval.ms': 1200000,  # 20分钟,避免_MAX_POLL_EXCEEDED,
}


class KnowledgeFileContextTaskListener(BaseListener):

    def __init__(self, instance_num):
        super().__init__(instance_num, **knowledge_file_context_task_listener_config)
