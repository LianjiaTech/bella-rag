import pytest

from app.services.file_service import file_indexing
from app.workers.handlers.knowledge_context_summary_task import knowledge_file_context_summary_callback
from bella_rag.utils.file_api_tool import file_api_client
from tests import TEST_PATH


@pytest.fixture(scope="module")
def test_file_id(auto_clean_files):
    """上传测试文件并返回file_id"""
    resources_dir = TEST_PATH + "/resources/"
    test_file_path = resources_dir + "测试.pdf"
    with open(test_file_path, 'rb') as file:
        file_bytes = file.read()
        file_info = file_api_client.upload_file(file_bytes, "测试.pdf", 'assistants')
        assert file_info is not None
        file_id = file_info["id"]
        auto_clean_files.append(test_file_id)
        file_indexing(file_id=file_id, file_name="测试.pdf", metadata={})

    yield file_id


def test_context_consume(test_file_id):
    payload = {
        "file_id": test_file_id,
        "request_id": test_file_id,
        "file_name": "测试.pdf",
        "extractors": [
            "context_extractor"
        ],
        "ucid": None
    }
    assert knowledge_file_context_summary_callback(payload)