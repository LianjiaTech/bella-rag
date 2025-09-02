from app.workers.handlers.knowledge_file_index_done_task import knowledge_file_summary_extract_callback
from bella_rag.transformations.extractor.extractors import EXTRACTOR_SUMMARY
from bella_rag.utils.file_api_tool import file_api_client
from bella_rag.utils.user_util import get_user_info
from tests import TEST_PATH

FILES = [
    "测试.csv",
    "测试.txt",
    "测试.pdf"
]


def test_knowledge_file_index_done_callback(auto_clean_files):
    """提取文件元数据"""
    for file_name in FILES:
        file_path = TEST_PATH + f'/resources/{file_name}'
        with open(file_path, 'rb') as file:
            file_bytes = file.read()
            file_info = file_api_client.upload_file(file_bytes, file_name, 'assistants')
            assert file_info is not None
            assert 'id' in file_info
            auto_clean_files.append(file_info['id'])
            message = {'file_id': file_info.get('id'),
                       "ucid": get_user_info(),
                       'file_name': file_name,
                       'extractors': [EXTRACTOR_SUMMARY]}
            assert knowledge_file_summary_extract_callback(message)
