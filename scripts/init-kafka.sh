#!/bin/bash
# Kafka初始化脚本

echo "Kafka初始化脚本执行..."

# 等待Kafka服务启动
echo "等待Kafka服务启动..."
while ! kafka-topics --bootstrap-server localhost:29092 --list >/dev/null 2>&1; do
    echo "Kafka服务尚未就绪，继续等待..."
    sleep 5
done

echo "Kafka服务已就绪"

# 创建kafka Topics
echo "创建Kafka Topics..."

# 监听知识索引任务的Topic
kafka-topics --create --topic knowledge-index-task --bootstrap-server localhost:29092 --partitions 3 --replication-factor 1 --if-not-exists
echo "Created topic: knowledge-index-task"

# 监听知识文件索引完成的Topic
kafka-topics --create --topic knowledge-file-index-done --bootstrap-server localhost:29092 --partitions 3 --replication-factor 1 --if-not-exists
echo "Created topic: knowledge-file-index-done"

# 监听文件删除的Topic
kafka-topics --create --topic knowledge-file-delete --bootstrap-server localhost:29092 --partitions 3 --replication-factor 1 --if-not-exists
echo "Created topic: knowledge-file-delete"

echo "本地Kafka Topics创建完成"

# 列出所有创建的topics
echo "当前kafka中的topics:"
kafka-topics --bootstrap-server localhost:29092 --list

echo "Kafka初始化完成"