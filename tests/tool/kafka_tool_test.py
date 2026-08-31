from unittest.mock import patch

from common.tool.kafka_tool import KafkaConsumer


def test_kafka_consumer_resumes_from_last_committed_offset():
    """
    消费必须从上次提交偏移量开始：暂停消费期间堆积的消息在恢复后必须被
    重新消费，而不是被跳过。earliest 只影响无提交偏移量时的起点。
    """
    with patch('common.tool.kafka_tool.Consumer') as mock_consumer:
        KafkaConsumer(
            bootstrap_servers='localhost:9092',
            group_id='test-group',
            topic='test-topic',
            callback=lambda payload: True,
            callback_timeout=1,
        )
    conf = mock_consumer.call_args[0][0]
    assert conf['auto.offset.reset'] == 'earliest'
    assert conf['enable.auto.commit'] is False
