import multiprocessing
import os

# 基础配置
port = os.getenv("PORT", 8080)
app_name = os.getenv("APP_NAME", "bella-rag")
print(f"{app_name} port:{port}")

bind = "0.0.0.0:%s" % port  # 绑定的ip与端口
backlog = 512  # 监听队列数量，64-2048

# 超时配置
timeout = int(os.getenv("GUNICORN_TIMEOUT", 600))  # 请求超时时间，默认10分钟
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", 5))  # Keep-Alive 连接超时时间
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", 300))  # 优雅重启超时时间

# 生产环境专用配置
worker_tmp_dir = os.getenv("GUNICORN_WORKER_TMP_DIR", None)  # worker临时目录

# Worker 配置
worker_class = os.getenv("GUNICORN_WORKER_CLASS", 'gthread')
max_workers = int(os.getenv("GUNICORN_MAX_WORKERS", 4))
workers = min(multiprocessing.cpu_count(), max_workers)
threads = int(os.getenv("GUNICORN_THREADS", 2))
worker_connections = int(os.getenv("GUNICORN_WORKER_CONNECTIONS", 500))

# 性能优化和内存管理
preload_app = os.getenv("GUNICORN_PRELOAD_APP", "False").lower() == "true"
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", 100))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", 20))

# 日志配置
loglevel = os.getenv("GUNICORN_LOG_LEVEL", 'info')
access_log_format = '%(t)s %(p)s %(h)s "%(r)s" %(s)s %(L)s %(b)s %(f)s" "%(a)s"'

logroot = os.getenv("MATRIX_APPLOGS_DIR", os.path.dirname(os.path.abspath(__file__)))
print(f"{app_name} logroot:{logroot}")
os.makedirs(logroot, exist_ok=True)  # 确保日志目录存在
accesslog = "%s/gunicorn_access.log" % logroot
errorlog = "%s/gunicorn_error.log" % logroot

proc_name = f'{app_name}-api'  # 进程名

# 输出配置信息
print(f"{app_name} Gunicorn 配置: workers={workers}, threads={threads}, worker_class={worker_class}, timeout={timeout}s")
print(f"资源配置: max_requests={max_requests}, worker_connections={worker_connections}")
print(f"CPU核心数: {multiprocessing.cpu_count()}, 实际worker数: {workers}")
