from init.settings import redis_handle, redis_keones_logging_sql_logs_key
import logging


class RedisLoggingSqlHandler(logging.Handler):
    def __init__(self, **kwargs):
        logging.Handler.__init__(self)

    def emit(self, record):
        try:
            # 格式化日志并指定编码为utf-8
            msg = self.format(record)  # msg是个str
            # kafka生产者，发送消息到broker。
            redis_handle.lpush(redis_keones_logging_sql_logs_key, msg)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)