import multiprocessing
import os

# 基础配置
port = os.getenv("PORT", 8080)
app_name = os.getenv("APP_NAME", "bella-rag")
print(f"{app_name} port:{port}")

bind = "0.0.0.0:%s" % port  # 绑定的ip与端口
backlog = 512  # 监听队列数量，64-2048

# 超时配置
timeout = int(os.getenv("GUNICORN_TIMEOUT", 1200))  # 请求超时时间，默认20分钟，gevent模式可以更长
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", 10))  # Keep-Alive 连接超时时间
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", 180))  # 优雅重启超时时间

# 生产环境专用配置
worker_tmp_dir = os.getenv("GUNICORN_WORKER_TMP_DIR", None)  # worker临时目录

# Worker 配置
worker_class = os.getenv("GUNICORN_WORKER_CLASS", 'sync')  # sync模式
max_workers = int(os.getenv("GUNICORN_MAX_WORKERS", 4))
workers = min(max(multiprocessing.cpu_count() // 2, 2), max_workers)  # 通常CPU核心数的一半即可

# 性能优化和内存管理
preload_app = os.getenv("GUNICORN_PRELOAD_APP", "false").lower() == "true"
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", 1000))  # 减少重启频率
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", 100))  # 随机重启范围

# Worker模式配置
if worker_class == 'sync':
    print(f"使用sync模式: {workers} workers（类似manage.py runserver但支持多进程）")
    print(f"总并发能力: {workers} 个同时处理的请求")
else:
    threads = int(os.getenv("GUNICORN_THREADS", 4))
    print(f"使用{worker_class}模式: {workers} workers, {threads} threads")

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
print(f"{app_name} Gunicorn 配置: workers={workers}, worker_class={worker_class}, timeout={timeout}s")
print(f"资源配置: max_requests={max_requests}")
print(f"CPU核心数: {multiprocessing.cpu_count()}, 实际worker数: {workers}")
