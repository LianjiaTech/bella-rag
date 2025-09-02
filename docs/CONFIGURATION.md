# 配置说明文档

## 概述

本项目支持灵活的配置管理，可以通过配置文件或环境变量来设置各种参数。配置项分为必需配置和可选配置两类。

## 配置文件

项目使用INI格式的配置文件，位于`conf/`目录下：

- `config_local.ini` - 本地开发环境配置
- `config_test.ini` - 测试环境配置  
- `config_release.ini` - 生产环境配置
- `config_opensource.ini` - 开源项目标准配置模板

## 环境变量覆盖

所有配置项都支持通过环境变量覆盖，格式为：`{SECTION}_{KEY}`

例如：
```bash
# 覆盖数据库主机配置
export DB_HOST=your-mysql-host

# 覆盖OpenAI API Key
export OPENAPI_AK="Bearer your-openai-key"

# 覆盖Elasticsearch主机
export ELASTICSEARCH_HOSTS=http://your-es-host:9200
```

## 必需配置

以下配置项是系统运行的必需配置，必须正确设置：

### 数据库配置 [DB]
```ini
[DB]
host = localhost          # MySQL主机地址
port = 3306              # MySQL端口
username = root          # 数据库用户名
password = your_password # 数据库密码
dbname = ke_rag         # 数据库名称
```

### Redis配置 [REDIS]
```ini
[REDIS]
host = localhost    # Redis主机地址
port = 6379        # Redis端口
password =         # Redis密码（可选）
database = 0       # Redis数据库编号
```

### OpenAI配置 [OPENAPI]
```ini
[OPENAPI]
ak = Bearer your_openai_api_key        # OpenAI API密钥
api_base = https://api.openai.com/v1   # API基础URL
```

### 向量数据库配置 [VECTOR_DB]
```ini
[VECTOR_DB]
url =                    # 向量数据库URL
key =                    # 访问密钥
database_name =          # 数据库名称
dimension =              # 向量维度
collection_name =        # 集合名称
embedding_model =        # 嵌入模型名称
```


## 可选配置

以下配置项为可选，如果不需要相关功能可以省略或留空：

### Elasticsearch配置 [ELASTICSEARCH]

**标准Elasticsearch配置：**
```ini
[ELASTICSEARCH]
hosts = http://localhost:9200  # ES集群地址
username =                     # ES用户名（可选）
password =                     # ES密码（可选）
index_name = ke_rag           # 索引名称
```


### S3存储配置 [S3]
用于开启解析过程ocr识别
```ini
[S3]
access_key =       # S3访问密钥
secret_key =       # S3私有密钥
bucket_name =      # 存储桶名称
endpoint =         # S3端点URL
region =           # 区域
image_domain =     # 图片域名
```

### Kafka配置 [KAFKA]
用于打通file-api的文件上传通路
```ini
[KAFKA]
bootstrap_servers = localhost:9092              # Kafka服务器地址
knowledge_index_topic = knowledge-index-task    # 知识索引主题
knowledge_file_index_done_topic = knowledge-file-index-done
knowledge_file_delete_topic = knowledge-file-delete
file_api_topic = file-api-task
```

### 重排序配置 [RERANK]
```ini
[RERANK]
api_base =              # 重排序API地址
model =                 # 重排序模型名称
rerank_num = 20         # 重排序数量
rerank_threshold = 0.99 # 重排序阈值
```

### OCR配置 [OCR]
```ini
[OCR]
model_name = gpt-4o  # OCR模型名称
enable = true        # 是否启用OCR
```

## 快速开始

1. 复制配置模板：
   ```bash
   cp conf/config_release.ini conf/config_local.ini
   ```

2. 修改必需配置项：
   ```bash
   # 编辑配置文件
   vim conf/config_local.ini
   
   # 或使用环境变量
   export DB_HOST=localhost
   export DB_PASSWORD=your_password
   export OPENAPI_AK="Bearer your_openai_key"
   ```

3. 启动服务：
   ```bash
   python manage.py runserver
   ```

## 配置验证

项目启动时会自动验证必需配置项，如果缺少必需配置会显示错误信息：

```
ValueError: 必需的配置项不存在: [DB].host
```

可选配置项如果不存在会使用默认值或设为None，不影响系统启动。

## 配置最佳实践

1. **开发环境**：使用配置文件，便于调试和修改
2. **生产环境**：使用环境变量，提高安全性
3. **容器部署**：推荐使用环境变量或ConfigMap
4. **敏感信息**：如API密钥、数据库密码等，建议使用环境变量或密钥管理服务

## 故障排除

### 常见问题

1. **配置文件不存在**
   ```
   FileNotFoundError: 配置文件不存在: /path/to/config.ini
   ```
   解决：检查配置文件路径是否正确

2. **必需配置缺失**
   ```
   ValueError: 必需的配置项不存在: [SECTION].key
   ```
   解决：添加缺失的配置项

3. **配置值类型错误**
   ```
   ValueError: invalid literal for int() with base 10: 'abc'
   ```
   解决：检查配置值格式是否正确

### 调试配置

启用调试模式查看配置加载过程：
```bash
export DEBUG=true
python manage.py runserver
```

配置加载信息会在启动日志中显示。 