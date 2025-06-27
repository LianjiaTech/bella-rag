"""
改进的Django settings，使用新的配置管理器
支持可选配置项和环境变量覆盖
"""

import json
import logging
import logging.config
import logging.handlers
import os
import sys

from common.tool.common_func import *
from common.tool.config_manager import init_config, get_config
from init.const import *

SERVER_START_TIME = get_current_time()
CURRENT_DATE = get_current_date()

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
print("BASE_DIR: %s" % BASE_DIR)

# 判断是否是生产环境
isRelease = os.getenv("ENVTYPE") == "prod"
print("线上环境：%s" % isRelease)

# 选择配置文件
conf_file = ""
if isRelease:
    conf_file = "%s/conf/config_release.ini" % BASE_DIR
    print("读取配置文件：config_release.ini")
elif os.getenv("CONFIG_FILE"):
    conf_file = "%s/conf/%s" % (BASE_DIR, os.getenv("CONFIG_FILE"))
    print("读取配置文件：%s" % os.getenv("CONFIG_FILE"))
elif is_linux():
    conf_file = "%s/conf/config_test.ini" % BASE_DIR
    print("读取配置文件：config_test.ini")
elif is_windows():
    conf_file = "%s/conf/config_local.ini" % BASE_DIR
    print("读取配置文件：config_local.ini")
else:
    conf_file = "%s/conf/config_local_mac.ini" % BASE_DIR
    print("读取配置文件：config_local_mac.ini")

# 初始化配置管理器
config = init_config(conf_file)
print("配置初始化完成")

#######################################################################################
# 数据库配置 - 必需
DB_HOST = config.get_required('DB', 'host')
DB_PORT = config.get_required('DB', 'port', int)
DB_USERNAME = config.get_required('DB', 'username')
DB_PASSWORD = config.get_required('DB', 'password')
DB_NAME = config.get_required('DB', 'dbname')
print("DB_HOST[%s] DB_PORT[%s] DB_USERNAME[%s] DB_PASSWORD[%s] DB_NAME[%s]" % (
    DB_HOST, DB_PORT, DB_USERNAME, DB_PASSWORD, DB_NAME))

# 日志目录配置
dirfile_log = config.get('DIRFILE', 'logroot', '/tmp/logs')
applogsdir = os.getenv("MATRIX_APPLOGS_DIR", "/tmp/applogs")
if applogsdir and os.path.isdir(applogsdir):
    log_root = applogsdir.rstrip("/")
else:
    log_root = dirfile_log.rstrip("/")
    if not os.path.exists(log_root):
        os.makedirs(log_root, exist_ok=True)

print("log_root:%s" % log_root)

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'ovjmbwl$ses4)++0+@mp79^8v27n+5&p*8pq32cr*0*or6migi'

DJANGO_INFO_LOG = "django_info.log"
DJANGO_ERROR_LOG = "django_error.log"

DEBUG = not isRelease
ALLOWED_HOSTS = eval(config.get('COMMON', 'allowed_host', "['*']"))

INSTALLED_APPS = APPS


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 以下为自定义中间件
    'common.middleware.traffice.TrafficMiddleware',
    'common.middleware.exception.ExceptionMiddleware',
]

# 日志配置
log_formaters = {
        'verbose': {
            'format': '%(asctime)s %(levelname)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'datestart': {
            'format': '%(asctime)s %(message)s'
        },
        'simple': {
            'format': '%(message)s'
        },
        'datestart_with_USERLOGGER': {
            'format': '%(asctime)s USERLOGGER %(levelname)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'datestart_with_TRACELOGGER': {
            'format': '%(message)s'
        },
        'datestart_with_ELAPSEDLOGGER': {
            'format': '%(asctime)s ELAPSEDLOGGER %(message)s'
        },
        'datestart_with_KAFKAASYNCLOGGER': {
            'format': '%(asctime)s KAFKAASYNCLOGGER %(message)s'
        },
    }
if is_linux():
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': log_formaters,
        'filters': {
            'require_debug_true': {
                '()': 'django.utils.log.RequireDebugTrue',
            },
        },
        'handlers': {
            # 默认日志
            'default': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',  # 保存到文件，自动切
                'filename': os.path.join(log_root, DJANGO_INFO_LOG),  # 日志文件
                'maxBytes': 1024 * 1024 * 50,  # 日志大小 50M
                'backupCount': 3,  # 最多备份几个
                'formatter': 'datestart_with_USERLOGGER',
                'encoding': 'utf-8',
            },
            'trace': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',  # 保存到文件，自动切
                'filename': os.path.join(log_root, "trace_info.log"),  # 日志文件
                'maxBytes': 1024 * 1024 * 50,  # 日志大小 50M
                'backupCount': 3,  # 最多备份几个
                'formatter': 'datestart_with_TRACELOGGER',
                'encoding': 'utf-8',
            },
            # 错误日志
            'error': {
                'level': 'ERROR',
                'class': 'logging.handlers.RotatingFileHandler',  # 保存到文件，自动切
                'filename': os.path.join(log_root, DJANGO_ERROR_LOG),  # 日志文件
                'maxBytes': 1024 * 1024 * 50,  # 日志大小 50M
                'backupCount': 3,  # 最多备份几个
                'formatter': 'verbose',
                'encoding': 'utf-8',
            },
            # 流量日志
            'traffic': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',  # 保存到文件，自动切
                'filename': os.path.join(log_root, DJANGO_INFO_LOG),  # 日志文件
                'maxBytes': 1024 * 1024 * 50,  # 日志大小 50M
                'backupCount': 3,  # 最多备份几个
                'formatter': 'datestart',
                'encoding': 'utf-8',
            },
            # sql日志
            'sql': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',  # 保存到文件，自动切
                'filename': os.path.join(log_root, DJANGO_INFO_LOG),  # 日志文件
                'maxBytes': 1024 * 1024 * 50,  # 日志大小 50M
                'backupCount': 3,  # 最多备份几个
                'formatter': 'datestart',
                'encoding': 'utf-8',
            },
            # 函数耗时日志
            'elapsed': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',  # 保存到文件，自动切
                'filename': os.path.join(log_root, DJANGO_INFO_LOG),  # 日志文件
                'maxBytes': 1024 * 1024 * 50,  # 日志大小 50M
                'backupCount': 3,  # 最多备份几个
                'formatter': 'datestart_with_ELAPSEDLOGGER',
                'encoding': 'utf-8',
            },
            # 函数耗时日志
            'kafkaasync': {
                'level': 'DEBUG',
                'class': 'common.logging_handler.redis_kafkaasync_handler.RedisLoggingKafkaasyncHandler',  # 保存到文件，自动切
                'formatter': 'datestart_with_KAFKAASYNCLOGGER',
                'encoding': 'utf-8',
            },
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['console', 'default'],
                'level': 'INFO',
                'propagate': True
            },
            'userlog': {
                'handlers': ['default'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'errorlog': {
                'handlers': ['error'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'trafficlog': {
                'handlers': ['traffic'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'sqllog': {
                'handlers': ['sql'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'elapsedlog': {
                'handlers': ['elapsed'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'kafkaasynclog': {
                'handlers': ['kafkaasync'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'tracelog': {
                'handlers': ['trace'],
                'level': 'DEBUG',
                'propagate': True,
            }
        },
    }
else:
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': log_formaters,
        'filters': {
            'require_debug_true': {
                '()': 'django.utils.log.RequireDebugTrue',
            },
        },
        'handlers': {
            # 终端输出
            'console': {
                'level': 'DEBUG',
                'filters': ['require_debug_true'],  # 只有在Django debug为True时才在屏幕打印日志
                'class': 'logging.StreamHandler',  #
                'formatter': 'verbose'
            },
            'console_simple': {
                'level': 'DEBUG',
                'filters': ['require_debug_true'],  # 只有在Django debug为True时才在屏幕打印日志
                'class': 'logging.StreamHandler',  #
                'formatter': 'simple'
            },
            # 默认日志
            'default': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',  # 保存到文件，自动切
                'filename': os.path.join(log_root, DJANGO_INFO_LOG),  # 日志文件
                'maxBytes': 1024 * 1024 * 50,  # 日志大小 50M
                'backupCount': 3,  # 最多备份几个
                'formatter': 'datestart_with_USERLOGGER',
                'encoding': 'utf-8',
            },
            'trace': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',  # 保存到文件，自动切
                'filename': os.path.join(log_root, "trace_info.log"),  # 日志文件
                'maxBytes': 1024 * 1024 * 50,  # 日志大小 50M
                'backupCount': 3,  # 最多备份几个
                'formatter': 'datestart_with_TRACELOGGER',
                'encoding': 'utf-8',
            },
            # 错误日志
            'error': {
                'level': 'ERROR',
                # 'class': 'common.logging_handler.redis_error_handler.RedisLoggingErrorHandler',  # 保存到文件，自动切

                'class': 'logging.handlers.RotatingFileHandler',  # 保存到文件，自动切
                'filename': os.path.join(log_root, "django_error.log"),  # 日志文件
                'maxBytes': 1024 * 1024 * 50,  # 日志大小 50M
                'backupCount': 3,  # 最多备份几个

                'formatter': 'verbose',
                'encoding': 'utf-8',
            },
            # 流量日志
            'traffic': {
                'level': 'DEBUG',
                # 'class': 'common.logging_handler.kafka_logging_handler.KafkaLoggingTrafficHandler',  # 保存到文件，自动切
                # 'class': 'common.logging_handler.redis_traffic_handler.RedisLoggingTrafficHandler',  # 保存到文件，自动切

                'class': 'logging.handlers.RotatingFileHandler',  # 保存到文件，自动切
                'filename': os.path.join(log_root, "django_traffic.log"),  # 日志文件
                'maxBytes': 1024 * 1024 * 50,  # 日志大小 50M
                'backupCount': 3,  # 最多备份几个

                'formatter': 'datestart',
                'encoding': 'utf-8',
            },
            # sql日志
            'sql': {
                'level': 'DEBUG',
                # 'class': 'common.logging_handler.redis_sql_handler.RedisLoggingSqlHandler',  # 保存到文件，自动切

                'class': 'logging.handlers.RotatingFileHandler',  # 保存到文件，自动切
                'filename': os.path.join(log_root, "django_sql.log"),  # 日志文件
                'maxBytes': 1024 * 1024 * 50,  # 日志大小 50M
                'backupCount': 3,  # 最多备份几个

                'formatter': 'datestart',
                'encoding': 'utf-8',
            },
            # 函数耗时日志
            'elapsed': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',  # 保存到文件，自动切
                'filename': os.path.join(log_root, "django_elapsed.log"),  # 日志文件
                'maxBytes': 1024 * 1024 * 50,  # 日志大小 50M
                'backupCount': 3,  # 最多备份几个
                'formatter': 'datestart_with_ELAPSEDLOGGER',
                'encoding': 'utf-8',
            },
            # 函数耗时日志
            'kafkaasync': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',  # 保存到文件，自动切
                'filename': os.path.join(log_root, "django_kafkaasync.log"),  # 日志文件
                'maxBytes': 1024 * 1024 * 50,  # 日志大小 50M
                'backupCount': 3,  # 最多备份几个
                'formatter': 'datestart_with_KAFKAASYNCLOGGER',
                'encoding': 'utf-8',
            },
        },
        'loggers': {
            '': {  # root logger
                'handlers': ['console', 'default'],
                'level': 'INFO',
                'propagate': True
            },
            'userlog': {
                'handlers': ['console', 'default'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'errorlog': {
                'handlers': ['console', 'error'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'trafficlog': {
                'handlers': ['traffic'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'sqllog': {
                'handlers': ['sql'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'elapsedlog': {
                'handlers': ['elapsed'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'kafkaasynclog': {
                'handlers': ['console','kafkaasync'],
                'level': 'DEBUG',
                'propagate': True,
            },
            'tracelog':{
                'handlers': ['trace', 'console'],
                'level': 'DEBUG',
                'propagate': True,
            }
        },
    }

ROOT_URLCONF = 'init.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'template')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'init.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': DB_NAME,
        'USER': DB_USERNAME,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
        'OPTIONS': {
            'charset': 'utf8mb4',
        }
    },
    'offline-readonly': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': DB_NAME,
        'USER': DB_USERNAME,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
        'OPTIONS': {
            'charset': 'utf8mb4',
        }
    }
}

# Redis配置 - 必需
REDIS_HOST = config.get_required('REDIS', 'host')
REDIS_PORT = config.get_required('REDIS', 'port', int)
REDIS_PWD = config.get('REDIS', 'password', '')
REDIS_DATABASE = config.get('REDIS', 'database', 0, int)

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://%s:%s" % (REDIS_HOST, REDIS_PORT),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100, "decode_responses": True},
            "PASSWORD": REDIS_PWD,
        }
    }
}

# OpenAI配置 - 必需
OPENAI = {
    'URL': config.get_required('OPENAPI', 'api_base'),
    'AK': config.get_required('OPENAPI', 'ak'),
}

# 向量数据库配置 - 必需
TENCENT_VECTOR_DB = {
    'URL': config.get('TENCENT_VECTOR_DB', 'url'),
    'KEY': config.get('TENCENT_VECTOR_DB', 'key'),
    'DATABASE_NAME': config.get('TENCENT_VECTOR_DB', 'database_name'),
    'DIMENSION': config.get('TENCENT_VECTOR_DB', 'dimension', 1024, int),
    'COLLECTION_NAME': config.get('TENCENT_VECTOR_DB', 'collection_name'),
    'SUMMARY_QUESTION_COLLECTION_NAME': config.get('TENCENT_VECTOR_DB', 'summary_question_collection_name'),
    'EMBEDDING_MODEL': config.get('TENCENT_VECTOR_DB', 'embedding_model'),
    'QUESTIONS_COLLECTION_NAME': config.get('TENCENT_VECTOR_DB', 'questions_collection_name')
}

# Elasticsearch配置 - 支持两种模式
if config.has_section('ELASTICSEARCH'):
    es_config = {}
    # 标准ES配置
    if config.has_option('ELASTICSEARCH', 'hosts'):
        es_config.update({
            'HOSTS': config.get('ELASTICSEARCH', 'hosts', 'http://localhost:9200'),
            'USERNAME': config.get('ELASTICSEARCH', 'username', ''),
            'PASSWORD': config.get('ELASTICSEARCH', 'password', ''),
            'INDEX_NAME': config.get('ELASTICSEARCH', 'index_name', 'ke_rag'),
        })
    # 业务定制ES配置（向后兼容）
    if config.has_option('ELASTICSEARCH', 'search_url'):
        es_config.update({
            'SEARCH_URL': config.get('ELASTICSEARCH', 'search_url'),
            'SEARCH_TOKEN': config.get('ELASTICSEARCH', 'search_token'),
            'DATA_URL': config.get('ELASTICSEARCH', 'data_url'),
            'DATA_TOKEN': config.get('ELASTICSEARCH', 'data_token'),
            'VERSION': config.get('ELASTICSEARCH', 'version', 'v1.0'),
        })
    ELASTICSEARCH = es_config
else:
    ELASTICSEARCH = None

# S3配置 - 可选
if config.has_section('S3'):
    S3_CONFIG = {
        'region_name': config.get('S3', 'region', 'cn-north-1'),
        'ak': config.get('S3', 'access_key', ''),
        'sk': config.get('S3', 'secret_key', ''),
        'endpoint': config.get('S3', 'endpoint', ''),
        'bucket_name': config.get('S3', 'bucket_name', ''),
        'image_domain': config.get('S3', 'image_domain', ''),
    }
else:
    S3_CONFIG = None

# Kafka配置 - 可选
if config.has_section('KAFKA'):
    KAFKA = {
        'KNOWLEDGE_INDEX_TASK_BOOTSTRAP_SERVERS': config.get('KAFKA', 'knowledge_index_task_bootstrap_servers', ''),
        'KNOWLEDGE_INDEX_TASK_TOPIC': config.get('KAFKA', 'knowledge_index_task_topic', ''),
        'KNOWLEDGE_INDEX_GROUP_ID': config.get('KAFKA', 'knowledge_index_group_id', ''),

        'KNOWLEDGE_FILE_INDEX_DONE_BOOTSTRAP_SERVERS': config.get('KAFKA', 'knowledge_file_index_done_bootstrap_servers', ''),
        'KNOWLEDGE_FILE_INDEX_DONE_TOPIC': config.get('KAFKA', 'knowledge_file_index_done_topic', ''),
        'KNOWLEDGE_FILE_INDEX_DONE_GROUP_ID': config.get('KAFKA', 'knowledge_file_index_done_group_id', ''),

        'FILE_API_TASK_BOOTSTRAP_SERVERS': config.get('KAFKA', 'file_api_bootstrap_servers', ''),
        'FILE_API_TASK_TOPIC': config.get('KAFKA', 'file_api_topic', ''),
        'FILE_API_TASK_GROUP_ID': config.get('KAFKA', 'file_api_group_id', ''),

        'KNOWLEDGE_FILE_CONTEXT_TASK_GROUP_ID': config.get('KAFKA', 'knowledge_file_index_context_group_id', ''),

        'KNOWLEDGE_FILE_DELETE_BOOTSTRAP_SERVERS': config.get('KAFKA', 'knowledge_file_delete_bootstrap_servers', ''),
        'KNOWLEDGE_FILE_DELETE_TOPIC': config.get('KAFKA', 'knowledge_file_delete_topic', ''),
        'KNOWLEDGE_FILE_DELETE_GROUP_ID': config.get('KAFKA', 'knowledge_file_delete_group_id', ''),
    }
else:
    KAFKA = None

# 重排序配置 - 可选
if config.has_section('RERANK'):
    RERANK = {
        'URL': config.get('RERANK', 'api_base', ''),
        'MODEL': config.get('RERANK', 'model', ''),
        'RERANK_NUM': config.get('RERANK', 'rerank_num', 20, int),
        'RERANK_THRESHOLD': config.get('RERANK', 'rerank_threshold', 0.99, float),
    }
else:
    RERANK = None

# 检索配置
RETRIEVAL = {
    'RETRIEVAL_NUM': config.get('RETRIEVAL', 'retrieval_num', 50, int),
    'TOKEN_THRESHOLD': config.get('RETRIEVAL', 'complete_token_threshold', 0.6, float),
    'COMPLETE_MAX_TOKEN': config.get('RETRIEVAL', 'complete_max_token', 1500, int),
    'MATCH_SCORE': config.get('RETRIEVAL', 'match_score', 0.95, float),
}

# 上下文总结配置
CONTEXT_SUMMARY = {
    'SPILT_MAX_LENGTH': config.get('CONTEXT_SUMMARY', 'spilt_max_length', 1500, int),
    'MAX_BACKGROUND_LENGTH': config.get('CONTEXT_SUMMARY', 'max_background_length', 20000, int),
    'OVERLAP_LENGTH': config.get('CONTEXT_SUMMARY', 'overlap_length', 2000, int),
    'MERGE_MIN_LENGTH': config.get('CONTEXT_SUMMARY', 'merge_min_length', 1000, int),
    'MERGE_MAX_LENGTH': config.get('CONTEXT_SUMMARY', 'merge_max_length', 1500, int),
    'FORCE_MERGE_LENGTH': config.get('CONTEXT_SUMMARY', 'force_merge_length', 300, int),
    'SUMMARY_MAX_BATCH_SIZE': config.get('CONTEXT_SUMMARY', 'summary_max_batch_size', 30, int),
}

# 可选服务配置
FILE_API = {
    'url': config.get('FILE_API', 'url', '')
} if config.has_section('FILE_API') else None

DOCUMENT_PARSE = {
    'url': config.get('DOCUMENT_PARSE', 'url', '')
} if config.has_section('DOCUMENT_PARSE') else None

OAUTH = {
    'url': config.get('OAUTH', 'url', ''),
    'client_id': config.get('OAUTH', 'client_id', ''),
    'client_secret': config.get('OAUTH', 'client_secret', ''),
} if config.has_section('OAUTH') else None

OCR = {
    'model_name': config.get('OCR', 'model_name', 'gpt-4o'),
    'enable': config.get('OCR', 'enable', True, bool),
} if config.has_section('OCR') else None

# Apollo配置 - 可选
APOLLO = {
    'APP_ID': config.get('APOLLO', 'APP_ID', ''),
    'PORTAL_SERVER_URL': config.get('APOLLO', 'PORTAL_SERVER_URL', ''),
    'CONFIG_SERVER_URL': config.get('APOLLO', 'CONFIG_SERVER_URL', ''),
    'AUTHORIZATION': config.get('APOLLO', 'AUTHORIZATION', ''),
    'ENV': config.get('APOLLO', 'ENV', 'DEV'),
    'CYCLE_TIME': config.get('APOLLO', 'CYCLE_TIME', 5, int),
} if config.has_section('APOLLO') else None

# 缓存配置
CACHE = {
    'CAPACITY': config.get('CACHE', 'capacity', 10000, int),
}

# 默认用户
DEFAULT_USER = config.get('USER', 'default_user', 'ke-rag')

# 国际化配置
LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = False

# 静态文件配置
STATIC_URL = '/static/'
STATICFILES_DIRS = {}

# Redis缓存超时配置
REDIS_TIMEOUT = 7 * 24 * 60 * 60
CUBES_REDIS_TIMEOUT = 60 * 60
NEVER_REDIS_TIMEOUT = 365 * 24 * 60 * 60

# 创建Redis连接
from django_redis import get_redis_connection
django_redis_default_conn = get_redis_connection("default")

from common.tool.my_redis_cache import MyRedisCache
redis_handle = MyRedisCache(django_redis_default_conn)

# 跨域配置
CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = True
CORS_ORIGIN_WHITELIST = ('*')

CORS_ALLOW_METHODS = (
    'DELETE',
    'GET',
    'POST',
    'PUT',
    'OPTIONS',
    'PATCH',
    'HEAD',
)

CORS_ALLOW_HEADERS = (
    'XMLHttpRequest',
    'X_FILENAME',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
)

trace_logger = logging.getLogger('tracelog')
user_logger = logging.getLogger('userlog')
error_logger = logging.getLogger('errorlog')
traffic_logger = logging.getLogger('trafficlog')
sql_logger = logging.getLogger('sqllog')
elapsed_logger = logging.getLogger('elapsedlog')
kafkaasync_logger = logging.getLogger('kafkaasynclog')
print("@@@@@@@@@@@@@@@@@@@@ END init.settings.py @@@@@@@@@@@@@@@@@@@@")
