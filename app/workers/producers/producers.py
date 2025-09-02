from typing import Optional, Dict

from common.tool.kafka_tool import KafkaProducer
from init.settings import KAFKA, user_logger

# 配置日志
logger = user_logger

# 生产者配置映射表
PRODUCER_CONFIG_MAP: Dict[str, Dict[str, str]] = {
    "knowledge_index_task": {
        "bootstrap_servers": "KNOWLEDGE_INDEX_TASK_BOOTSTRAP_SERVERS",
        "topic": "KNOWLEDGE_INDEX_TASK_TOPIC"
    },
    "knowledge_file_extractor": {
        "bootstrap_servers": "KNOWLEDGE_FILE_INDEX_DONE_BOOTSTRAP_SERVERS",
        "topic": "KNOWLEDGE_FILE_INDEX_DONE_TOPIC"
    },
    "knowledge_file_delete": {
        "bootstrap_servers": "KNOWLEDGE_FILE_DELETE_BOOTSTRAP_SERVERS",
        "topic": "KNOWLEDGE_FILE_DELETE_TOPIC"
    }
}


def get_kafka_producer(producer_type: str) -> Optional[KafkaProducer]:
    """获取指定类型的Kafka生产者实例"""

    config = PRODUCER_CONFIG_MAP.get(producer_type)
    if not config:
        logger.error(f"未知的生产者类型: {producer_type}")
        return None

    # 获取配置参数
    bs_key = config["bootstrap_servers"]
    topic_key = config["topic"]

    bootstrap_servers = KAFKA.get(bs_key)
    topic = KAFKA.get(topic_key)

    if not all([bootstrap_servers, topic]):
        logger.warning(f"Kafka配置不完整 ({producer_type}): 需要 {bs_key} 和 {topic_key}")
        return None

    try:
        return KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            topic=topic
        )
    except Exception as e:
        logger.error(f"Kafka生产者初始化失败 ({producer_type}): {str(e)}",
                     exc_info=True)
        return None


# 初始化所有生产者
producers = {pt: get_kafka_producer(pt) for pt in PRODUCER_CONFIG_MAP}
logger.info(f'kafka producers init success : {producers}')

knowledge_index_task_kafka_producer = producers["knowledge_index_task"]
knowledge_file_extractor_producer = producers["knowledge_file_extractor"]
knowledge_file_delete_producer = producers["knowledge_file_delete"]


def async_send_kafka_message(producer: KafkaProducer, data: str):
    if not producer:
        logger.warn(f'producer is none, can not send message: {data}')
        return False

    return producer.sync_send_message(data)
