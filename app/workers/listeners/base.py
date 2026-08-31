from concurrent.futures import ThreadPoolExecutor, TimeoutError

from common.tool.kafka_tool import KafkaConsumer
from init.settings import KAFKA, user_logger

logger = user_logger


class BaseListener(KafkaConsumer):
    _enable = True  # 是否可启动
    # 声明受“向量索引重建期间暂停消费”开关门控的监听器设置其配置键；None 表示不受门控
    consume_switch_key = None

    def __init__(self, instance_num, **task_config):
        if task_config['bootstrap_servers'] is None or task_config['topic'] is None or task_config['group_id'] is None:
            logger.info("Kafka配置不完整，无法创建Listener实例: bootstrap_servers=%s topic=%s group_id=%s",
                        task_config['bootstrap_servers'], task_config['topic'], task_config['group_id'])
            self._enable = False
        elif not self._consume_enabled():
            logger.info("消费开关已关闭，跳过创建Listener: switch=%s listener=%s",
                        self.consume_switch_key, self.__class__.__name__)
            self._enable = False
        else:
            super().__init__(**task_config)
            # callback执行线程池，工作线程数设置需适当高于kafka消费线程数
            self.callback_executor = ThreadPoolExecutor(max_workers=3 * instance_num)

    @classmethod
    def _consume_enabled(cls) -> bool:
        """未声明开关的监听器始终可消费；声明了开关的以配置值为准。"""
        if cls.consume_switch_key is None:
            return True
        return KAFKA.get(cls.consume_switch_key, True)

    @classmethod
    def get_instance(cls, instance_num: int):
        """
        使用get_instance方法创建时候必须实现一个无参的构造方法
        """
        instance_arr = []
        for i in range(instance_num):
            instance = cls(instance_num)
            if instance._enable:
                logger.info("创建kafka消费者 topic=%s group_id=%s 实例【%s】", instance.topic, instance.group_id, i)
                instance_arr.append(instance)
            else:
                logger.info("Listener %s 实例【%s】不可用，跳过创建", cls.__name__, i)
        return instance_arr

    def run_callback(self, payload, **kwargs) -> bool:
        future = self.callback_executor.submit(self.callback, payload, **kwargs)
        try:
            # 设置超时时间，单位为秒
            # todo python的future超时后不会中断任务，设置超时时间防止重平衡导致任务无限消费
            return future.result(timeout=self.callback_timeout)
        except TimeoutError:
            future.cancel()
            logger.warn("callback执行超时 consumer topic: [%s] message: %s", self.topic, payload)
            return False
