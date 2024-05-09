from init.settings import redis_handle, redis_keones_logging_error_logs_key
import logging


class RedisLoggingErrorHandler(logging.Handler):
    def __init__(self, **kwargs):
        logging.Handler.__init__(self)

    def emit(self, record):
        try:
            # 格式化日志并指定编码为utf-8
            msg = self.format(record)  # msg是个str
            # kafka生产者，发送消息到broker。
            # 对msg大小进行处理，超过1.9M的进行截取
            max_respones_size = int(1024 * 1024 * 1.8)
            # max_respones_size = 10
            msg = msg if len(msg) <= max_respones_size else msg[: max_respones_size]
            redis_handle.lpush(redis_keones_logging_error_logs_key, msg)
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception:
            self.handleError(record)
