#!/bin/bash

# MySQL 数据库初始化脚本

echo "开始初始化MySQL数据库..."

# 等待MySQL服务完全启动
sleep 5

# 执行数据库初始化SQL脚本
mysql -h mysql -u root -p${MYSQL_ROOT_PASSWORD:-root_password} < /scripts/init_database.sql

if [ $? -eq 0 ]; then
    echo "数据库初始化成功！"
else
    echo "数据库初始化失败！"
    exit 1
fi

echo "MySQL数据库初始化完成。"
