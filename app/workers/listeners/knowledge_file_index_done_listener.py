from app.workers.handlers.knowledge_file_index_done_task import knowledge_file_summary_extract_callback
from app.workers.listeners.base import BaseListener
from app.workers.producers.producers import knowledge_file_extractor_producer
from init.settings import KAFKA

knowledge_file_index_done_listener_config = {
    "bootstrap_servers": KAFKA.get("KNOWLEDGE_FILE_INDEX_DONE_BOOTSTRAP_SERVERS", None),
    "group_id": KAFKA.get("KNOWLEDGE_FILE_INDEX_DONE_GROUP_ID", None),
    "topic": KAFKA.get("KNOWLEDGE_FILE_INDEX_DONE_TOPIC", None),
    "callback": knowledge_file_summary_extract_callback,
    "callback_timeout": 550,  # 执行超时时间（秒）
    "producer": knowledge_file_extractor_producer,  # 消息重试producer
    "max.poll.interval.ms": 600000,  # 10分钟,避免_MAX_POLL_EXCEEDED
    "err_retry_max": 4,
    "retry_interval": 30,
}


class KnowledgeFileIndexDoneListener(BaseListener):

    def __init__(self, instance_num):
        super().__init__(instance_num, **knowledge_file_index_done_listener_config)
