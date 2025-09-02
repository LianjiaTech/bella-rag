import datetime
import os

import django
import pytest

from tests import TEST_PATH

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "init.settings")  # 替换为你的 Django 项目的设置模块
django.setup()
print("@@@@@@@@@@@@@@@@@@@@@@@@@ ★★★INIT DJANGO SETTINGS★★★ @@@@@@@@@@@@@@@@@@@@@@@@@")
from app.common.contexts import TraceContext
from init.settings import OPENAPI
from bella_rag.utils.file_api_tool import file_api_client

from app.workers import stop_workers

def pytest_sessionstart(session):
    print(f"pytest_sessionstart called at {datetime.datetime.now()}")
    print(f"Session object: {session}")
    TraceContext.trace_id = "mock_trace_id"
    os.environ["OPENAI_API_KEY"] = OPENAPI["AK"]
    os.environ["OPENAI_BASE_URL"] = OPENAPI["URL"]


def pytest_sessionfinish(session):
    print("pytest_sessionfinish - 测试结束后")
    stop_workers()


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
