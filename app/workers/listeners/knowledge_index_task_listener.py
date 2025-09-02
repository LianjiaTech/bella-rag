from app.workers.handlers.knowledge_index_task import knowledge_index_task_callback
from app.workers.listeners.base import BaseListener
from app.workers.producers.producers import knowledge_index_task_kafka_producer
from init.settings import KAFKA

knowledge_index_task_config = {
    "bootstrap_servers": KAFKA.get("KNOWLEDGE_INDEX_TASK_BOOTSTRAP_SERVERS", None),
    "group_id": KAFKA.get("KNOWLEDGE_INDEX_GROUP_ID", None),
    "topic": KAFKA.get("KNOWLEDGE_INDEX_TASK_TOPIC", None),
    "callback": knowledge_index_task_callback,
    "callback_timeout": 2300,  # 执行超时时间（秒）
    "producer": knowledge_index_task_kafka_producer,  # 消息重试producer
    'max.poll.interval.ms': 2400000,  # 40分钟,避免_MAX_POLL_EXCEEDED
}


class KnowledgeIndexTaskListener(BaseListener):

    def __init__(self, instance_num):
        super().__init__(instance_num, **knowledge_index_task_config)
