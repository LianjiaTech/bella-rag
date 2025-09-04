#!/bin/bash
# Elasticsearch初始化脚本 - ke-RAG项目

echo "Elasticsearch初始化脚本执行..."

# 等待Elasticsearch服务启动
echo "等待Elasticsearch服务启动..."
until curl -s "http://elasticsearch:9200/_cluster/health" >/dev/null 2>&1; do
    echo "Elasticsearch服务尚未就绪，继续等待..."
    sleep 5
done

echo "Elasticsearch服务已就绪"

# 设置ES主机和索引名称
ES_HOST="http://elasticsearch:9200"
INDEX_NAME="bella_rag"

echo "正在创建ke-RAG索引: $INDEX_NAME"

# 检查索引是否已存在
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$ES_HOST/$INDEX_NAME")

if [ "$HTTP_STATUS" -eq 200 ]; then
    echo "索引 '$INDEX_NAME' 已存在，跳过创建"
else
    echo "创建新索引 '$INDEX_NAME'..."
    
    # ke-RAG索引映射配置（简化版，不依赖ik分词器）
    INDEX_MAPPING='{
      "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
          "analyzer": {
            "standard_analyzer": {
              "type": "standard"
            }
          }
        }
      },
      "mappings": {
        "properties": {
          "type": {
            "type": "keyword",
            "index": true
          },
          "relationships": {
            "type": "text",
            "index": false
          },
          "source_id": {
            "type": "keyword",
            "index": true
          },
          "content": {
            "type": "text",
            "analyzer": "standard",
            "index": true
          },
          "source_name": {
            "type": "text",
            "analyzer": "standard",
            "index": true,
            "fields": {
              "keyword": {
                "type": "keyword",
                "ignore_above": 256
              }
            }
          },
          "extra": {
            "type": "text",
            "index": false
          },
          "node_type": {
            "type": "keyword",
            "index": true
          },
          "text": {
            "type": "text",
            "analyzer": "standard",
            "index": true
          },
          "metadata": {
            "type": "object",
            "dynamic": true
          }
        }
      }
    }'
    
    # 创建索引
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X PUT \
      -H "Content-Type: application/json" \
      "$ES_HOST/$INDEX_NAME" \
      -d "$INDEX_MAPPING")
    
    if [ "$HTTP_STATUS" -eq 200 ] || [ "$HTTP_STATUS" -eq 201 ]; then
        echo "✅ 索引 '$INDEX_NAME' 创建成功"
        
        # 验证索引创建
        echo "验证索引结构..."
        INDEX_INFO=$(curl -s "$ES_HOST/$INDEX_NAME/_mapping")
        if echo "$INDEX_INFO" | grep -q "source_id"; then
            echo "✅ 索引结构验证成功"
        else
            echo "⚠️  索引结构验证失败，但索引已创建"
        fi
        
    else
        echo "❌ 索引创建失败，HTTP状态码: $HTTP_STATUS"
        echo "继续执行，索引可以在应用启动时动态创建"
    fi
fi

echo "Elasticsearch初始化完成"
echo "索引名称: $INDEX_NAME"
echo "ES地址: $ES_HOST"
