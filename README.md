# Bella-RAG

> Bella-RAG是一个基于Django的开源RAG（Retrieval-Augmented Generation）框架，提供文档理解、索引构建、检索问答等完整的RAG基础能力。

## 🚀 特性

### 🏆 核心技术优势

- **🔥 业界领先的文档解析**: 文档结构化解析效果业界领先，支持复杂版面和多模态内容理解
- **🎯 高精度检索技术**: 利用多路召回和small2big技术，兼顾语义检索效果与信息完整度，多场景验证综合结果可用率 > 85%
- **🧠 Contextual RAG增强**: 支持Contextual RAG技术，在chunk编码前预先添加解释性的上下文信息，大幅提升检索准确率
- **🚀 Deep RAG智能agent模式**: 基于Planning and Solve模式的智能agent，通过自动制定执行计划（确认文件范围 -> 阅读文件 -> 反思）、步骤式执行和动态重规划，实现比传统RAG更优的问答效果
- **🔧 策略插件化架构**: 检索策略完全可插拔，调用方可根据业务场景灵活调整检索策略及参数，满足不同领域需求

### 🛠️ 系统特性

- **多格式文档支持**: 支持PDF、Word、Excel、HTML、Markdown等多种文档格式
- **向量化存储**: 集成Qdrant向量数据库（开源版）或腾讯向量数据库（企业版），提供高效的向量存储和检索
- **安全的混合架构**: 向量数据库仅存储向量，原始内容安全存储在MySQL中
- **灵活的检索策略**: 支持多种检索模式和重排序算法
- **可扩展架构**: 模块化设计，易于扩展和定制
- **完整的API**: 提供完整的RESTful API接口
- **异步处理**: 支持Kafka异步任务处理
- **可选ES支持**: 可选择集成Elasticsearch进行全文检索
- **一键初始化**: 提供自动化脚本快速完成环境配置


## 🏗️ 系统架构

### 整体架构图

![系统架构图](docs/images/system-architecture.png)![img.png](框架图.png)


### 处理流程图
![img.png](流程图.png)
*从文档上传到检索问答的完整处理流程*

### 数据存储架构

ke-RAG采用混合存储架构，将数据安全性和检索效率相结合：

**向量数据库（Qdrant/腾讯云向量数据库）**：
- 存储文档和问答的向量化表示
- 不存储原始文本内容（安全考虑）
- 支持高效的相似度检索
- 包含三个集合：主文档向量、QA向量、文档总结向量
- 支持使用Qdrant自部署，或者企业版的腾讯云向量数据库

**关系型数据库（MySQL）**：
- 存储文档的原始内容和元数据
- 提供结构化数据查询能力
- 确保数据的持久性和一致性

**搜索引擎（Elasticsearch，可选）**：
- 提供全文检索能力
- 补充向量检索的不足
- 支持复杂的文本查询和过滤

架构优势：
1. **安全性**：敏感文档内容不暴露在向量数据库中
2. **性能**：向量检索和关键词检索各司其职
3. **灵活性**：支持多种检索策略的组合
4. **可扩展性**：各组件可独立扩展


## ⚡ 快速开始

### 🐋 Docker Compose 一键部署（推荐）

```bash
# 1. 克隆项目
git clone https://github.com/your-org/ke-RAG.git
cd ke-RAG

# 2. 配置环境变量（可选）
export OPENAI_API_KEY="your_openai_api_key"
export OPENAI_API_BASE="https://api.openai.com/v1"

# 3. 启动所有服务
docker-compose up -d

# 4. 检查服务状态
docker-compose ps

# 5. 验证服务健康状态
curl http://localhost:8008/api/actuator/health/liveness
```

### 🎯 向量数据库选择

ke-RAG 支持多种向量数据库，您可以根据需求选择：

#### 🔥 Qdrant（开源版，推荐）
- ✅ **完全开源免费**：MIT许可证，无使用限制
- ✅ **本地部署**：数据完全可控，无需依赖第三方服务
- ✅ **一键启动**：Docker Compose 自动部署和初始化
- ✅ **高性能**：Rust编写，内存占用低，检索速度快
- ✅ **易扩展**：支持水平扩展和分布式部署

#### 🏢 腾讯云向量数据库（企业版）
- ✅ **托管服务**：无需运维，自动备份和高可用
- ✅ **企业级**：支持大规模数据和高并发访问
- ✅ **完整生态**：与腾讯云其他服务深度集成
- ⚙️ **需要配置**：需要腾讯云账号和API密钥

#### 配置说明
```bash
# 默认使用Qdrant
docker-compose up -d

# 使用腾讯向量数据库需要修改配置文件
# 编辑 conf/config_docker.ini：
[VECTOR_DB]
type = tencent  # 改为 tencent

[TENCENT_VECTOR_DB]
url = your_tencent_vectordb_url
key = your_api_key
database_name = your_database
# ... 其他配置
```

### 📝 基本使用示例

```bash
# 1. 索引文档
curl --location 'http://localhost:8008/api/file/indexing' \
  --header 'Authorization: Bearer {OPEN_API_KEY}' \
  --header 'Content-Type: application/json' \
  --data '{
    "file_id": "test-file-001",
    "file_name": "example.md",
    "user": "1000000029406069"
  }'

# 2. 检索问答
curl --location 'http://localhost:8008/api/rag/search' \
  --header 'Authorization: Bearer {OPEN_API_KEY}' \
  --header 'Content-Type: application/json' \
  --data '{
    "query": "你好",
    "scope": [
        {
            "type": "file",
            "ids": [
                "FILE_ID"
            ]
        }
    ],
    "limit": 3,
    "user": "user_00000000",
    "mode": "ultra"
}'
```

## 📋 环境要求

- **Docker** >= 20.0
- **Docker Compose** >= 2.0  
- **可用内存** >= 4GB
- **OpenAI API密钥**（或兼容的API服务）

> 💡 **提示**: 所有服务通过 Docker Compose 一键部署，无需手动安装 MySQL、Redis、Qdrant 等组件

## 🔧 配置说明

### Contextual RAG增强配置

ke-RAG支持先进的Contextual RAG技术，可以在chunk编码前为每个文档片段添加上下文信息：

- 上下文预处理：为每个chunk添加文档级别的上下文描述
- 智能摘要：自动生成文档结构和主题信息
- 提升检索语义理解能力，减少断章取义

## 📚 使用指南

### API接口

服务启动后，可以通过以下接口使用：

#### 1. 健康检查
```bash
GET /api/actuator/health/liveness
```

#### 2. 文档索引
```bash
POST /api/file/indexing
Content-Type: application/json
Authorization: Bearer {token}

{
    "query": "你好",
    "scope": [
        {
            "type": "file",
            "ids": [
                "FILE_ID"
            ]
        }
    ],
    "limit": 3
}
```

#### 3. 检索问答
```bash
POST /api/rag/search
Content-Type: application/json
Authorization: Bearer {token}

{
    "query": "你的问题",
    "file_ids": ["file1", "file2"],
    "top_k": 5
}
```

## 🔧 开发指南

### 项目结构

```
ke-RAG/
├── app/                    # Django应用
│   ├── models/            # 数据模型
│   ├── services/          # 业务逻辑
│   └── handlers/          # 请求处理
├── bella_rag/                # 核心RAG框架
│   ├── transformations/   # 数据转换
│   ├── vector_stores/     # 向量存储
│   └── llm/              # 大模型接口
├── common/                # 公共工具
├── conf/                  # 配置文件
├── docker-compose.yml     # Docker编排
└── scripts/              # 初始化脚本
```

### 扩展开发

1. **添加新的向量存储**: 继承 `VectorStore` 基类
2. **自定义检索策略**: 实现 `RetrievalStrategy` 接口
3. **新增文档解析器**: 扩展 `DocumentParser` 类

## 🐛 故障排除

### 常见问题

1. **服务启动失败**
   - 检查Docker和Docker Compose版本
   - 确保端口8008、3306、6379、6333等未被占用
   - 查看日志：`docker-compose logs`

2. **Elasticsearch连接失败**
   - 确保Elasticsearch服务正常启动
   - 检查网络连接和配置

3. **向量数据库连接问题**
   - 验证API密钥和URL配置
   - 检查网络连通性

4. **内存不足**
   - 确保系统可用内存 >= 4GB
   - 根据需要调整Docker内存限制

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs bella-rag-api

# 实时查看日志
docker-compose logs -f
```

## 📄 许可证

本项目采用 [MIT许可证](LICENSE)。

## 🤝 贡献

我们欢迎各种形式的贡献！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 更新日志

### v1.0.0 (2025-08-25)
- 🎉 首个正式版本发布
- ✨ 支持多种向量数据库（Qdrant、腾讯向量数据库）
- 🔧 Docker Compose一键部署
- 📚 完整的API接口和文档
