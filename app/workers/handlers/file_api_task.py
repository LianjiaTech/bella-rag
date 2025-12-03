import json

from app.config.apollo_configs import file_access_config
from app.postprocessors.file_postprocessors import FileSummaryProcessor, FileIndexingProcessor
from app.services.file_service import file_delete_submit_task
from bella_rag.utils.openapi_util import _fetch_ak_info
from common.helper.exception import FileNotFoundException
from init.settings import user_logger
from bella_rag.utils.file_api_tool import file_api_client

file_api_postprocessors = [FileIndexingProcessor(), FileSummaryProcessor()]
valid_file_purposes = {'assistants', 'assistants-chat'}
file_event_handlers = {
    # 发送删除事件
    "file.deleted": lambda file_id: file_delete_submit_task(file_id),
    # 更新文件状态为消息入队
    "file.created": lambda file_id: file_api_client.update_processing_status(
        'queued', 0, file_id, '', "file_indexing"
    )
}

def enable_file(ak_code: str, ak_info: dict = None) -> bool:
    if not file_access_config.enable_ak_code_filter():
        return True
    if not ak_code:
        return False
    if ak_code in file_access_config.enable_ak_codes():
        return True
    # 检查parent ak code是否准入
    if not ak_info:
        ak_info = _fetch_ak_info(ak_code)
    parent_code = ak_info.get('parentCode') if ak_info else None
    if parent_code and parent_code in file_access_config.enable_ak_codes():
        return True
    return False


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

    if not data:
        return True

    file_id = data.get('id')
    if data.get('purpose') in valid_file_purposes:
        handler = file_event_handlers.get(payload.get('event'))
        if handler:
            handler(file_id)
            return True

    # 关注domtree的事件变更
    if data.get('purpose') != 'dom_tree' or payload.get('event') != "file.created":
        return True

    # 查询ak信息
    ak_code = payload.get('ak_code')
    ak_info = _fetch_ak_info(ak_code) if ak_code else None

    if not enable_file(ak_code, ak_info):
        file_api_client.update_processing_status('access_denied', 0, file_id, f'ak_code : {ak_code} is not enabled for file indexing', "file_indexing")
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

    # 设置akSha
    if ak_info:
        payload['ak_sha'] = ak_info.get('akSha')

    for post_processor in file_api_postprocessors:
        post_processor.post_process(payload)
    return True
