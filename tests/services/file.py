from app.services import rag_service,file_service
from app.services.file_service import redis_client, deleted_files_key
from bella_rag.utils.user_util import get_user_info


def test_file_edit(test_file_id):
    file_id = test_file_id('md')
    file_service.file_indexing(file_id=file_id, file_name="测试.md", metadata={}, user=get_user_info())
    file_service.rename_file(file_id, "我认知中的bella-rename.md")
    print("rename file success")

    city_list = ["临沂", "济南", "青岛"]
    chunk = {
        "extra": {
            "city_list": city_list,
            "hidden": True
        }
    }
    file_service.file_update(file_id, **chunk)
    print("update chunk by source id success")


def test_record_deleted_file():
    # 测试 file_id 为空的情况
    file_service.record_deleted_file('')
    file_service.record_deleted_file('mock_file123')
    redis_client.sadd.assert_called_once_with(deleted_files_key, 'mock_file123')

def test_remove_deleted_files_record():
    # 测试 file_ids 为空的情况
    file_service.remove_deleted_files_record([])
    redis_client.srem.assert_not_called()

    file_service.remove_deleted_files_record(['mock_file123', 'mock_file456'])
    redis_client.srem.assert_any_call(deleted_files_key, 'file123')
    redis_client.srem.assert_any_call(deleted_files_key, 'file456')


def test_filter_deleted_files():
    file_ids = ['mock_file1', 'mock_file2', 'mock_file3']
    file_service.record_deleted_file('mock_file1')

    result = file_service.filter_deleted_files(file_ids)
    assert result == ['mock_file2', 'mock_file3']
