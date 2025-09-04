#!/bin/bash

# ke-RAG腾讯向量数据库初始化脚本
# 用法: ./bin/init_vectordb.sh

echo "=========================================="
echo "ke-RAG 腾讯向量数据库初始化工具"
echo "=========================================="
echo "此脚本将帮助您创建ke-RAG所需的三个向量集合"
echo ""

# 获取用户输入
read -p "请输入向量数据库URL: " VECTORDB_URL
read -p "请输入API密钥: " API_KEY
read -p "请输入数据库名称: " DATABASE_NAME
read -p "请输入向量维度 [1024]: " DIMENSION
DIMENSION=${DIMENSION:-1024}

read -p "请输入主文档集合名称 [document_vectors]: " MAIN_COLLECTION
MAIN_COLLECTION=${MAIN_COLLECTION:-document_vectors}

read -p "请输入QA问答集合名称 [qa_vectors]: " QA_COLLECTION
QA_COLLECTION=${QA_COLLECTION:-qa_vectors}

read -p "请输入文档总结集合名称 [summary_vectors]: " SUMMARY_COLLECTION
SUMMARY_COLLECTION=${SUMMARY_COLLECTION:-summary_vectors}

read -p "请输入副本数 [2]: " REPLICA_NUM
REPLICA_NUM=${REPLICA_NUM:-2}

read -p "请输入分片数 [10]: " SHARD_NUM
SHARD_NUM=${SHARD_NUM:-10}

echo ""
echo "配置信息："
echo "向量数据库URL: $VECTORDB_URL"
echo "数据库名称: $DATABASE_NAME"
echo "向量维度: $DIMENSION"
echo "主文档集合: $MAIN_COLLECTION"
echo "QA问答集合: $QA_COLLECTION"
echo "文档总结集合: $SUMMARY_COLLECTION"
echo "副本数: $REPLICA_NUM"
echo "分片数: $SHARD_NUM"
echo ""

read -p "确认创建这些集合? (y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "操作已取消"
    exit 0
fi

# 检查curl是否可用
if ! command -v curl &> /dev/null; then
    echo "错误: 未找到curl命令，请确保curl已安装"
    exit 1
fi

# 创建主文档向量集合
echo ""
echo "正在创建主文档向量集合..."
curl -i -X POST \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer account=root&api_key=$API_KEY" \
  $VECTORDB_URL/collection/create \
  -d "{
    \"database\": \"$DATABASE_NAME\",
    \"collection\": \"$MAIN_COLLECTION\",
    \"replicaNum\": $REPLICA_NUM,
    \"shardNum\": $SHARD_NUM,
    \"description\": \"主文档向量集合\",
    \"indexes\": [
        {
            \"fieldName\": \"id\",
            \"fieldType\": \"string\",
            \"indexType\": \"primaryKey\"
        },
        {
            \"fieldName\": \"vector\",
            \"fieldType\": \"vector\",
            \"indexType\": \"HNSW\",
            \"dimension\": $DIMENSION,
            \"metricType\": \"COSINE\",
            \"params\": {
                \"M\": 16,
                \"efConstruction\": 200
            }
        },
        {
            \"fieldName\": \"source_id\",
            \"fieldType\": \"string\",
            \"indexType\": \"filter\"
        },
        {
            \"fieldName\": \"source_name\",
            \"fieldType\": \"string\",
            \"indexType\": \"filter\"
        },
        {
            \"fieldName\": \"node_type\",
            \"fieldType\": \"string\",
            \"indexType\": \"filter\"
        },
        {
            \"fieldName\": \"extra\",
            \"fieldType\": \"array\",
            \"indexType\": \"filter\"
        },
        {
            \"fieldName\": \"relationships\",
            \"fieldType\": \"string\",
            \"indexType\": \"filter\"
        }
    ]
}"

echo ""
echo "主文档向量集合创建完成"

# 创建QA问答向量集合
echo ""
echo "正在创建QA问答向量集合..."
curl -i -X POST \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer account=root&api_key=$API_KEY" \
  $VECTORDB_URL/collection/create \
  -d "{
    \"database\": \"$DATABASE_NAME\",
    \"collection\": \"$QA_COLLECTION\",
    \"replicaNum\": $REPLICA_NUM,
    \"shardNum\": $SHARD_NUM,
    \"description\": \"QA问答向量集合\",
    \"indexes\": [
        {
            \"fieldName\": \"id\",
            \"fieldType\": \"string\",
            \"indexType\": \"primaryKey\"
        },
        {
            \"fieldName\": \"vector\",
            \"fieldType\": \"vector\",
            \"indexType\": \"HNSW\",
            \"dimension\": $DIMENSION,
            \"metricType\": \"COSINE\",
            \"params\": {
                \"M\": 16,
                \"efConstruction\": 200
            }
        },
        {
            \"fieldName\": \"source_id\",
            \"fieldType\": \"string\",
            \"indexType\": \"filter\"
        },
        {
            \"fieldName\": \"source_name\",
            \"fieldType\": \"string\",
            \"indexType\": \"filter\"
        },
        {
            \"fieldName\": \"group_id\",
            \"fieldType\": \"string\",
            \"indexType\": \"filter\"
        },
        {
            \"fieldName\": \"extra\",
            \"fieldType\": \"array\",
            \"indexType\": \"filter\"
        }
    ]
}"

echo ""
echo "QA问答向量集合创建完成"

# 创建文档总结向量集合
echo ""
echo "正在创建文档总结向量集合..."
curl -i -X POST \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer account=root&api_key=$API_KEY" \
  $VECTORDB_URL/collection/create \
  -d "{
    \"database\": \"$DATABASE_NAME\",
    \"collection\": \"$SUMMARY_COLLECTION\",
    \"replicaNum\": $REPLICA_NUM,
    \"shardNum\": $SHARD_NUM,
    \"description\": \"文档总结向量集合\",
    \"indexes\": [
        {
            \"fieldName\": \"id\",
            \"fieldType\": \"string\",
            \"indexType\": \"primaryKey\"
        },
        {
            \"fieldName\": \"vector\",
            \"fieldType\": \"vector\",
            \"indexType\": \"HNSW\",
            \"dimension\": $DIMENSION,
            \"metricType\": \"COSINE\",
            \"params\": {
                \"M\": 16,
                \"efConstruction\": 200
            }
        },
        {
            \"fieldName\": \"source_id\",
            \"fieldType\": \"string\",
            \"indexType\": \"filter\"
        }
    ]
}"

echo ""
echo "文档总结向量集合创建完成"

echo ""
echo "=========================================="
echo "✅ 向量数据库初始化完成！"
echo "=========================================="
echo "已创建的集合："
echo "1. $MAIN_COLLECTION (主文档向量集合)"
echo "2. $QA_COLLECTION (QA问答向量集合)"
echo "3. $SUMMARY_COLLECTION (文档总结向量集合)"
echo ""
echo "请在配置文件中填写以下集合名称："
echo "collection_name = $MAIN_COLLECTION"
echo "questions_collection_name = $QA_COLLECTION"
echo "summary_question_collection_name = $SUMMARY_COLLECTION"
echo "==========================================" 