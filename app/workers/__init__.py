from concurrent.futures import ThreadPoolExecutor
from typing import List

from app.workers.listeners.file_api_listener import FileApiTaskListener
from app.workers.listeners.knowledge_file_context_task_listener import KnowledgeFileContextTaskListener
from app.workers.listeners.knowledge_file_delete_listener import KnowledgeFileDeleteListener
from app.workers.listeners.knowledge_file_index_done_listener import KnowledgeFileIndexDoneListener
from app.workers.listeners.knowledge_index_task_listener import KnowledgeIndexTaskListener
from app.workers.producers.producers import knowledge_index_task_kafka_producer, knowledge_file_extractor_producer
from common.tool.kafka_tool import KafkaConsumer
from init.settings import user_logger

logger = user_logger

consumers: List[KafkaConsumer] = []
consumers.extend(KnowledgeIndexTaskListener.get_instance(1))
consumers.extend(KnowledgeFileIndexDoneListener.get_instance(1))
consumers.extend(FileApiTaskListener.get_instance(1))
consumers.extend(KnowledgeFileDeleteListener.get_instance(1))
consumers.extend(KnowledgeFileContextTaskListener.get_instance(1))

# 线程池最大工作线程数
executor = None
if len(consumers) > 0:
    executor = ThreadPoolExecutor(max_workers=len(consumers))


def start_workers():
    # 提交任务到线程池
    for i, consumer in enumerate(consumers):
        logger.info("启动kafka消费者 topic=%s group_id=%s 实例【%s】", consumer.topic, consumer.group_id, i)
        executor.submit(consumer.consume_messages)


def stop_workers():
    for consumer in consumers:
        consumer.stop()
    executor.shutdown()


__all__ = ['knowledge_index_task_kafka_producer', 'knowledge_file_extractor_producer', 'start_workers', 'stop_workers','consumers','executor']
