import logging
from init.config import conf_dict
from common.tool.kafka_tool import KafkaTool
try:
    kafka_logging_traffic_handle = None
    # 日志收集相关topic
    kafka_key = "KAFKA"
    KAFKA_SERVERS = eval(conf_dict[kafka_key]['myservers'])
    KAFKA_LOGGING_TRAFFIC_TOPICS = eval(conf_dict[kafka_key]['logging_traffic_topic'])
    print("KAFKA_LOGGING_TRAFFIC_TOPICS:%s" % KAFKA_LOGGING_TRAFFIC_TOPICS)
    kafka_logging_traffic_handle = KafkaTool(KAFKA_SERVERS, KAFKA_LOGGING_TRAFFIC_TOPICS)
    kafka_logging_traffic_handle.create_producer()
except:
    print("KAFKA_LOGGING_TRAFFIC_TOPICS : 创建生产者失败！")


class KafkaLoggingTrafficHandler(logging.Handler):
    def __init__(self, **kwargs):
        logging.Handler.__init__(self)

    def emit(self, record):
        # 忽略kafka的日志，以免导致无限递归。
        if 'kafka' in record.name:
            return
        try:
            # 格式化日志并指定编码为utf-8
            msg = self.format(record)
            # kafka生产者，发送消息到broker。
            kafka_logging_traffic_handle.send_producer_msg(msg.encode("utf8"))
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)



