import json

from app.postprocessors.file_postprocessors import FileSummaryProcessor, FileIndexingProcessor
from common.helper.exception import FileNotFoundException
from init.settings import user_logger
from bella_rag.utils.file_api_tool import file_api_client

file_api_postprocessors = [FileIndexingProcessor(), FileSummaryProcessor()]


def file_api_task_callback(payload: dict) -> bool:
    """
    file api消息体结构
    {
        "event": "file.created",
        "data": {
            "id": "file-abc123",
            "object": "file",
            "bytes": 175,
            "created_at": 1613677385,
            "filename": "salesOverview.pdf",
            "purpose": "assistants",
        },
        "metadata": {
                "post_processors":["file_indexing"],
                "city_list":["北京"],
                "callbacks":[]
            }
    }
    业务方数据存储在metadata内部。bella侧定义了几种metadata参数
    """
    user_logger.info(f'receive event from file api : {json.dumps(payload)}')
    data = payload.get('data')

    # 当前只监听文件创建事件
    if not data:
        return True

    file_id = data.get('id')
    if payload.get('event') == "file.created" and data.get('purpose') in ['assistants', 'assistants-chat']:
        # 更新文件状态为消息入队
        file_api_client.update_processing_status('queued', 0, file_id, '', "file_indexing")
        return True

    # 关注domtree的事件变更
    if data.get('purpose') != 'dom_tree' or payload.get('event') != "file.created":
        return True

    # 根据domtree查找source文件信息
    domtree = file_api_client.parse_pdf_from_json(file_id)
    source_file_id = domtree.root.source_file.id
    try:
        # 查询文件的元信息
        source_file_info = file_api_client.get_file_info(source_file_id)
        payload['data']['id'] = source_file_id
        payload['data']['filename'] = source_file_info.get('filename')
        payload['metadata'] = source_file_info.get('metadata', "{}")
    except FileNotFoundException:
        user_logger.warn(f"源文件已删除，跳过解析 : {source_file_id}")
        return True

    for post_processor in file_api_postprocessors:
        post_processor.post_process(payload)
    return True
