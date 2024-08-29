import time

from kafka import KafkaConsumer
from kafka import KafkaProducer
from kafka import TopicPartition


class KafkaTool(object):
    def __init__(self, bootstrap_servers, topics=[]):
        # 消费者相关的属性
        self.topics = topics
        self.bootstrap_servers = bootstrap_servers
        self.group_id = ""
        self.client_id = ""
        self.auto_offset_reset = "latest"
        self.enable_auto_commit = True
        self.auto_commit_interval_ms = 0
        self.consumer_timeout_ms = 0

    def create_consumer(self):
        kwargs = {}
        kwargs["enable_auto_commit"] = self.enable_auto_commit

        if self.auto_commit_interval_ms:
            kwargs["auto_commit_interval_ms"] = self.auto_commit_interval_ms
        if self.consumer_timeout_ms:
            kwargs["consumer_timeout_ms"] = self.consumer_timeout_ms
        if self.bootstrap_servers:
            kwargs["bootstrap_servers"] = self.bootstrap_servers
        else:
            return False

        if self.topics:
            pass
        else:
            return False

        if self.group_id:
            kwargs["group_id"] = self.group_id
        if self.client_id:
            kwargs["client_id"] = self.client_id
        if self.auto_offset_reset:
            kwargs["auto_offset_reset"] = self.auto_offset_reset

        self.consumer = KafkaConsumer(*self.topics, **kwargs)

        return self.consumer

    def generate_consume_msg(self, max_item=0, stop_timestamp=0, stop_time=None):
        if self.consumer:
            consume_count = 0
            for msg in self.consumer:
                yield msg
                consume_count += 1
                if (max_item > 0 and consume_count >= max_item) or (
                        stop_timestamp > 0 and time.time() >= stop_timestamp) or (
                        stop_time is not None and time.time() >= time.mktime(
                    time.strptime(stop_time, "%Y-%m-%d %H:%M:%S"))):
                    # 如果满足最大消费次数 或者 最大时间戳 或者 截止时间，则退出
                    break

    def get_metrics(self):
        if self.consumer:
            return self.consumer.metrics()
        else:
            return None

    def create_producer(self):
        if self.bootstrap_servers:
            self.producer = KafkaProducer(bootstrap_servers=self.bootstrap_servers)
            return self.producer
        else:
            return False

    def close_producer(self):
        if hasattr(self, "producer"):
            self.producer.close()
            delattr(self, "producer")

    def send_producer_msg(self, value, topic=None, key=None, headers=None, partition=None, timestamp_ms=None):
        # 查看producer是否创建，如果没有创建就创建，重试5次
        for i in range(0, 5):
            try:
                if not hasattr(self, "producer"):
                    self.create_producer()
            except Exception as e:
                print(e)
            finally:
                if not hasattr(self, "producer"):
                    time.sleep(1)

        if topic:
            res = self.producer.send(topic, value, key=key, headers=headers, partition=partition,
                                     timestamp_ms=timestamp_ms)
            self.producer.flush()
            return res
        elif self.topics:
            res = self.producer.send(self.topics[0], value, key=key, headers=headers, partition=partition,
                                     timestamp_ms=timestamp_ms)
            self.producer.flush()
            return res
        else:
            return False


class KafkaConsumer:
    def __init__(self, bootstrap_servers, group_id, topic, callback):
        self.consumer = Consumer({
            'bootstrap.servers': bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest',  # 可以是 'earliest', 'latest', 'none'
            'enable.auto.commit': False,  # 禁用自动提交
            'max.poll.interval.ms': 600000,  # 10分钟,避免_MAX_POLL_EXCEEDED
        })
        self.topic = topic
        self.consumer.subscribe([self.topic])
        self.callback = callback
        self.err_cnt_max = 3
        self.__closed = False
        self.lock = threading.Lock()

    def create_consumer(self):
        kwargs = {}
        kwargs["enable_auto_commit"] = self.enable_auto_commit

        # if self.enable_auto_commit and self.auto_commit_interval_ms is not None:
        #     kwargs["auto_commit_interval_ms"] = self.auto_commit_interval_ms
        if self.consumer_timeout_ms:
            kwargs["consumer_timeout_ms"] = self.consumer_timeout_ms
        if self.bootstrap_servers:
            kwargs["bootstrap_servers"] = self.bootstrap_servers
        else:
            return False

        if self.topic:
            pass
        else:
            return False

        if self.group_id:
            kwargs["group_id"] = self.group_id
        if self.client_id:
            kwargs["client_id"] = self.client_id
        if self.auto_offset_reset:
            kwargs["auto_offset_reset"] = self.auto_offset_reset

        self.consumer = KafkaConsumer(*self.topic, **kwargs)

        return self.consumer

    def generate_consume_msg(self, max_item=0, stop_timestamp=0, stop_time=None):
        try:
            if self.consumer:
                consume_count = 0
                while True:
                    msg = next(self.consumer)
                    if msg == -1:
                        break
                    msg = self.consumer.poll(1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        logger.info("consume_messages PARTITION_EOF topic=%s partition=%s code=%s ",
                                    msg.topic(), msg.partition(), msg.error().code())
                    else:
                        logger.error("consume_messages error topic=%s partition=%s code=%s ",
                                     msg.topic(), msg.partition(), msg.error().code())
                else:
                    message_value = msg.value().decode("utf-8")
                    logger.info("Received topic: [%s] partition:[%s] message: %s",
                                self.topic, msg.partition(), message_value)
                    err_cnt = 0
                    while err_cnt < self.err_cnt_max:
                        try:
                            # 调用注册的回调方法
                            if self.callback(message_value):
                                # 手动提交偏移量
                                self.consumer.commit(msg)
                                logger.info("consumer topic: [%s] partition:[%s] message: %s 消费成功",
                                            self.topic, msg.partition(), message_value)
                                break
                            else:
                                err_cnt += 1
                                logger.info("consumer topic: [%s] partition:[%s] message: %s  retry=%s",
                                            self.topic, msg.partition(), message_value, err_cnt)
                        except Exception as e:
                            err_cnt += 1
                            logger.info("consumer  topic: [%s] partition:[%s] message: %s  retry=%s e=%s",
                                        self.topic, msg.partition(), message_value, err_cnt, e)
                            logger.exception(e)
                    if err_cnt == self.err_cnt_max:
                        logger.error("consumer fail topic: [%s] partition:[%s] 需要研发关注补偿: %s",
                                     self.topic, msg.partition(), message_value)
                        self.consumer.commit(msg)
        except KeyboardInterrupt:
            logger.error("用户中断")
        except KafkaError as e:
            logger.error("Kafka 错误: %s", e)
        except Exception as e:
            if e.args and e.args[0] == 'Consumer closed' and self.__closed:
                logger.info("Consumer closed topic: [%s]", self.topic)
            else:
                logger.error("Exception 错误: topic: [%s] error: %s", self.topic, e)
        finally:
            if not self.__closed:
                logger.info("workers topic = %s final close", self.topic)
                self.consumer.close()

                    yield msg
                    consume_count += 1
                    if not self.enable_auto_commit:
                        self.consumer.commit()
                    # self.consumer.commit(offsets={self.tp: (OffsetAndMetadata(end_offset + 1, None))})
                    print('Kafka partition: %s offset: %s' % (
                        msg.partition, self.consumer.committed(TopicPartition(msg.topic, msg.partition))))
                    if (max_item > 0 and consume_count >= max_item) or (
                            stop_timestamp > 0 and time.time() >= stop_timestamp) or (
                            stop_time is not None and time.time() >= time.mktime(
                        time.strptime(stop_time, "%Y-%m-%d %H:%M:%S"))):
                        # 如果满足最大消费次数 或者 最大时间戳 或者 截止时间，则退出
                        break
        except Exception as e:
            print(e)

    def get_metrics(self):
        if self.consumer:
            return self.consumer.metrics()
        else:
            return None

    def create_producer(self):
        if self.bootstrap_servers:
            self.producer = KafkaProducer(bootstrap_servers=self.bootstrap_servers)
            return self.producer
        else:
            return False

    def close_producer(self):
        if hasattr(self, "producer"):
            self.producer.close()
            delattr(self, "producer")

    def send_producer_msg(self, value, topic=None, key=None, headers=None, partition=None, timestamp_ms=None):
        # 查看producer是否创建，如果没有创建就创建，重试5次
        for i in range(0, 5):
            try:
                if not hasattr(self, "producer"):
                    self.create_producer()
            except Exception as e:
                print(e)
            finally:
                if not hasattr(self, "producer"):
                    time.sleep(1)

        if topic:
            res = self.producer.send(topic, value, key=key, headers=headers, partition=partition,
                                     timestamp_ms=timestamp_ms)
            self.producer.flush()
            return res
        elif self.topic:
            res = self.producer.send(self.topic, value, key=key, headers=headers, partition=partition,
                                     timestamp_ms=timestamp_ms)
            self.producer.flush()
            return res
        else:
            return False


if __name__ == "__main__":
    mytopics = ["plat-qa-wjltest"]
    myservers = ["kafka01-test.lianjia.com:9092", "kafka02-test.lianjia.com:9092", "kafka03-test.lianjia.com:9092"]
    kt = KafkaTool(myservers, mytopics)
