import os

NO_SIGN_URL = [
    "/pubCheck",
]

DEFAULT_DB_DATE = "1970-01-02"
DEFAULT_DB_TIME = "1970-01-02 00:00:00"

# redis key
redis_keones_logging_sql_logs_key = "keones_logging_sql_logs"  # logging sql key
redis_keones_logging_traffic_logs_key = "keones_logging_traffic_logs"
redis_keones_logging_error_logs_key = "keones_logging_error_logs"
redis_keones_logging_user_logs_key = "keones_logging_log_logs"
redis_keones_logging_elapsed_logs_key = "keones_logging_elapsed_logs"
redis_keones_logging_kafkaasync_logs_key = "keones_logging_kafkaasync_logs"

APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    # app 应用通过 manage.py 动态添加为 app.apps.AppConfig
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace("\\", "/")
SECRET_KEY = ''
