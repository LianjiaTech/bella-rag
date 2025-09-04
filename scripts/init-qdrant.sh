#!/bin/bash

# Qdrant向量数据库初始化脚本
# 创建ke-RAG系统所需的三个集合

set -e

# 配置参数
QDRANT_URL=${QDRANT_URL:-"http://qdrant:6333"}
API_KEY=${QDRANT_API_KEY:-""}
DIMENSION=${QDRANT_DIMENSION:-1024}

# 集合名称配置
MAIN_COLLECTION=${QDRANT_COLLECTION_NAME:-"documents"}
QA_COLLECTION=${QDRANT_QUESTIONS_COLLECTION_NAME:-"qa_documents"} 
SUMMARY_COLLECTION=${QDRANT_SUMMARY_COLLECTION_NAME:-"summary_documents"}

echo "=========================================="
echo "🚀 Qdrant向量数据库初始化"
echo "=========================================="
echo "Qdrant URL: $QDRANT_URL"
echo "向量维度: $DIMENSION"
echo "主文档集合: $MAIN_COLLECTION"
echo "QA文档集合: $QA_COLLECTION"
echo "摘要文档集合: $SUMMARY_COLLECTION"
echo "=========================================="

# 设置认证头
AUTH_HEADER=""
if [ ! -z "$API_KEY" ]; then
    AUTH_HEADER="-H \"api-key: $API_KEY\""
fi

# 等待Qdrant服务启动
echo "⏳ 等待Qdrant服务启动..."
for i in {1..30}; do
    if curl -s "$QDRANT_URL/health" > /dev/null 2>&1; then
        echo "✅ Qdrant服务已启动"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Qdrant服务启动超时"
        exit 1
    fi
    sleep 2
done

# 函数：创建集合
create_collection() {
    local collection_name=$1
    local description=$2
    local extra_fields=$3
    
    echo ""
    echo "📁 创建集合: $collection_name"
    
    # 检查集合是否已存在
    echo "检查集合是否存在..."
    if curl -s $AUTH_HEADER "$QDRANT_URL/collections/$collection_name" | grep -q "\"status\":\"ok\""; then
        echo "⚠️  集合 $collection_name 已存在，跳过创建"
        return 0
    fi
    
    # 构建payload字段配置
    local payload_schema=""
    if [ ! -z "$extra_fields" ]; then
        payload_schema=", \"payload_schema\": { $extra_fields }"
    fi
    
    # 创建集合
    local response=$(curl -s -w "%{http_code}" -X PUT \
        $AUTH_HEADER \
        -H "Content-Type: application/json" \
        "$QDRANT_URL/collections/$collection_name" \
        -d "{
            \"vectors\": {
                \"size\": $DIMENSION,
                \"distance\": \"Cosine\"
            },
            \"optimizers_config\": {
                \"default_segment_number\": 2,
                \"max_segment_size\": null,
                \"memmap_threshold\": null,
                \"indexing_threshold\": 20000,
                \"flush_interval_sec\": 5,
                \"max_optimization_threads\": 1
            },
            \"hnsw_config\": {
                \"m\": 16,
                \"ef_construct\": 200,
                \"full_scan_threshold\": 10000
            },
            \"wal_config\": {
                \"wal_capacity_mb\": 32,
                \"wal_segments_ahead\": 0
            },
            \"quantization_config\": null,
            \"init_from\": null,
            \"on_disk_payload\": true
            $payload_schema
        }")
    
    local http_code="${response: -3}"
    local body="${response%???}"
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo "✅ 集合 $collection_name 创建成功"
        
        # 创建索引（如果需要）
        if [ ! -z "$extra_fields" ]; then
            echo "📋 为集合 $collection_name 创建payload索引..."
            create_payload_indexes "$collection_name"
        fi
    else
        echo "❌ 集合 $collection_name 创建失败"
        echo "HTTP状态码: $http_code"
        echo "响应内容: $body"
        exit 1
    fi
}

# 函数：创建payload索引
create_payload_indexes() {
    local collection_name=$1
    
    # 为常用字段创建索引
    local fields=("source_id" "source_name" "node_type" "extra" "group_id")
    
    for field in "${fields[@]}"; do
        echo "🔍 为字段 $field 创建索引..."
        curl -s $AUTH_HEADER \
            -X PUT \
            -H "Content-Type: application/json" \
            "$QDRANT_URL/collections/$collection_name/index" \
            -d "{
                \"field_name\": \"$field\",
                \"field_schema\": \"keyword\"
            }" > /dev/null
    done
}

# 创建主文档向量集合
echo ""
echo "📚 创建主文档向量集合..."
create_collection "$MAIN_COLLECTION" "主文档向量集合" "
    \"source_id\": {\"type\": \"keyword\", \"index\": true},
    \"source_name\": {\"type\": \"text\", \"index\": true},
    \"node_type\": {\"type\": \"keyword\", \"index\": true},
    \"extra\": {\"type\": \"keyword\", \"index\": true},
    \"relationships\": {\"type\": \"text\", \"index\": false}
"

# 创建QA问答向量集合
echo ""
echo "❓ 创建QA问答向量集合..."
create_collection "$QA_COLLECTION" "QA问答向量集合" "
    \"source_id\": {\"type\": \"keyword\", \"index\": true},
    \"source_name\": {\"type\": \"text\", \"index\": true},
    \"group_id\": {\"type\": \"keyword\", \"index\": true},
    \"extra\": {\"type\": \"keyword\", \"index\": true}
"

# 创建文档总结向量集合
echo ""
echo "📄 创建文档总结向量集合..."
create_collection "$SUMMARY_COLLECTION" "文档总结向量集合" "
    \"source_id\": {\"type\": \"keyword\", \"index\": true}
"

echo ""
echo "=========================================="
echo "🎉 Qdrant向量数据库初始化完成！"
echo "=========================================="
echo "✅ 主文档集合: $MAIN_COLLECTION"
echo "✅ QA文档集合: $QA_COLLECTION"  
echo "✅ 摘要文档集合: $SUMMARY_COLLECTION"
echo ""
echo "📊 集合统计信息:"

# 显示集合信息
for collection in "$MAIN_COLLECTION" "$QA_COLLECTION" "$SUMMARY_COLLECTION"; do
    echo ""
    echo "📁 集合: $collection"
    collection_info=$(curl -s $AUTH_HEADER "$QDRANT_URL/collections/$collection")
    if echo "$collection_info" | grep -q "\"status\":\"ok\""; then
        echo "   状态: ✅ 正常"
        echo "   向量数量: $(echo "$collection_info" | grep -o '"vectors_count":[0-9]*' | cut -d':' -f2)"
        echo "   索引状态: $(echo "$collection_info" | grep -o '"status":"[^"]*"' | cut -d':' -f2 | tr -d '"')"
    else
        echo "   状态: ❌ 异常"
    fi
done

echo ""
echo "🌐 Qdrant WebUI: $QDRANT_URL/dashboard"
echo "📖 API文档: $QDRANT_URL/docs"
echo "=========================================="
