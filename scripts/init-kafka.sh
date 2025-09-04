#!/bin/bash
# Kafka初始化脚本

echo "Kafka初始化脚本执行..."

# 等待Kafka服务启动
echo "等待Kafka服务启动..."
while ! kafkacat -b localhost:9092 -L >/dev/null 2>&1; do
    echo "Kafka服务尚未就绪，继续等待..."
    sleep 5
done

echo "Kafka服务已就绪"

# 创建必要的Topic（如果需要）
echo "创建Kafka Topics..."

# 知识索引任务Topic
kafka-topics.sh --create --topic knowledge_index_task --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists

# 文件API任务Topic  
kafka-topics.sh --create --topic file_api_task --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists

# 知识文件删除Topic
kafka-topics.sh --create --topic knowledge_file_delete --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists

# 知识文件上下文任务Topic
kafka-topics.sh --create --topic knowledge_file_context_task --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists

# 知识问题重试Topic
kafka-topics.sh --create --topic knowledge_question_retry --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1 --if-not-exists

echo "Kafka Topics创建完成"
echo "Kafka初始化完成"
