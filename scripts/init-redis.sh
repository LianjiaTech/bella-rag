#!/bin/bash
# Redis初始化脚本

echo "Redis初始化脚本执行..."

# 等待Redis服务启动
until redis-cli ping >/dev/null 2>&1; do
    echo "等待Redis服务启动..."
    sleep 1
done

echo "Redis服务已就绪"

# 可以在这里添加Redis初始化命令，例如：
# redis-cli SET initial_key "initial_value"

echo "Redis初始化完成"