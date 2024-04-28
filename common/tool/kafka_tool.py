from kafka import KafkaConsumer
from kafka import KafkaProducer
from kafka import TopicPartition
from kafka.structs import OffsetAndMetadata
import time


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
        # self.consumer = None
        # self.producer = None

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
                if hasattr(self, "producer"):
                    break
                else:
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


class NewKafkaTool(object):
    def __init__(self, bootstrap_servers, topic=None, partition=None, group_id=None, enable_auto_commit=False):
        # 消费者相关的属性
        self.topic = topic if not isinstance(topic, str) else [topic]
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id if group_id else ""
        self.client_id = ""
        self.auto_offset_reset = "latest"
        self.enable_auto_commit = enable_auto_commit
        self.auto_commit_interval_ms = 0
        self.consumer_timeout_ms = 0
        self.partition = partition

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
                if hasattr(self, "producer"):
                    break
                else:
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
