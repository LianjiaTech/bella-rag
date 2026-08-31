import datetime
import os
import sys

import django
import pytest

from tests import TEST_PATH

# 必须在导入任何应用代码之前标记测试环境，关闭 import 期副作用：
# vector_db_tool 不连接真实向量库、AppConfig.ready() 不启动 kafka 消费者/定时任务。
os.environ.setdefault("RAG_TESTING", "1")

# manage.py 通过 APPS.append("app.apps.AppConfig") 动态注册 app 应用，
# pytest 直接 django.setup() 不会执行该逻辑，这里补上（对齐 manage.py 第22行）。
from init.const import APPS, BASE_DIR

if "app.apps.AppConfig" not in APPS:
    APPS.append("app.apps.AppConfig")


def _platform_config_file() -> str:
    """与 init/settings.py 的平台配置选择保持一致。"""
    if os.getenv("ENVTYPE") == "prod":
        return os.path.join(BASE_DIR, "conf", "config_release.ini")
    if sys.platform.startswith("linux"):
        return os.path.join(BASE_DIR, "conf", "config_test.ini")
    if sys.platform == "win32":
        return os.path.join(BASE_DIR, "conf", "config_local.ini")
    return os.path.join(BASE_DIR, "conf", "config_local_mac.ini")


_MINIMAL_LOCAL_CONFIG = """[DB]
host=127.0.0.1
port=3306
username=test
password=test
dbname=test

[REDIS]
host=127.0.0.1
port=6379

[OPENAPI]
api_base=http://localhost
ak=test-ak

[OCR]
vision_model_list=[]
"""


def _ensure_local_config() -> None:
    """init.settings 按平台选择配置文件；缺失时生成最小本地配置使测试可导入。

    仅提供让 settings 可导入的占位值，测试不连接这些服务。
    """
    conf_file = _platform_config_file()
    if os.path.exists(conf_file):
        return
    os.makedirs(os.path.dirname(conf_file), exist_ok=True)
    with open(conf_file, "w", encoding="utf-8") as handle:
        handle.write(_MINIMAL_LOCAL_CONFIG)


_ensure_local_config()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "init.settings")
django.setup()
print("@@@@@@@@@@@@@@@@@@@@@@@@@ ★★★INIT DJANGO SETTINGS★★★ @@@@@@@@@@@@@@@@@@@@@@@@@")
from app.common.contexts import TraceContext
from init.settings import OPENAPI
from bella_rag.utils.file_api_tool import file_api_client


def pytest_sessionstart(session):
    print(f"pytest_sessionstart called at {datetime.datetime.now()}")
    print(f"Session object: {session}")
    TraceContext.trace_id = "mock_trace_id"
    os.environ["OPENAI_API_KEY"] = OPENAPI["AK"]
    os.environ["OPENAI_BASE_URL"] = OPENAPI["URL"]


@pytest.fixture
def auto_clean_files():
    file_ids = []
    yield file_ids
    # 测试结束后执行清理
    for fid in file_ids:
        file_api_client.delete_file(fid)


@pytest.fixture
def test_file_id(auto_clean_files):
    """返回一个函数，用于获取测试文件ID并自动清理"""

    def _get_test_file_id(file_type):
        file_name = f'测试.{file_type.lower()}'
        test_file_path = TEST_PATH + f"/resources/{file_name}"

        with open(test_file_path, 'rb') as file:
            file_bytes = file.read()
            file_info = file_api_client.upload_file(file_bytes, file_name, 'assistants')
            assert file_info is not None
            file_id = file_info['id']
            auto_clean_files.append(file_id)  # 自动添加到清理列表
            return file_id

    return _get_test_file_id
