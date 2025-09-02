import json

from django.http import HttpResponse
from django.views.decorators.http import require_http_methods

from app.response.rag_response import OpenApiError
from app.services import chunk_service
from common.helper import ApiReturn
from init.settings import error_logger


@require_http_methods(["POST"])
def add_chunk(request):
    data = json.loads(request.body)
    source_id = data.get('source_id')
    source_name = data.get('source_name')
    content_title = data.get('content_title')
    content_data = data.get('content_data')
    chunk_pos = data.get('chunk_pos')
    chunk_type = data.get('chunk_type')
    extra = data.get('extra')
    if not source_id or not source_name or not content_title or not content_data or not chunk_type or chunk_pos is None:
        error = OpenApiError(message="require source_id, source_name, content_title, content_data, chunk_type, chunk_pos",
                             body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)
    try:
        chunk_id = chunk_service.add_chunk(source_id, source_name, content_title, content_data, chunk_type,
                                           chunk_pos, extra)
    except Exception as e:
        error_logger.error(f'add chunk : {data} error : {e}')
        error = OpenApiError(message="add chunk failed",
                             body={"code": ApiReturn.CODE_INNER_CODE, "type": "add_chunk_failed"})
        return HttpResponse(error.json_response(), status=500)
    return HttpResponse(ApiReturn(ApiReturn.CODE_OK, body={"chunk_id": chunk_id, "status": "success"}).to_json())


@require_http_methods(["POST"])
def delete_chunk(request):
    data = json.loads(request.body)
    chunk_id = data.get('chunk_id')
    if not chunk_id:
        error = OpenApiError(message="require chunk_id",
                             body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)
    try:
        chunk_service.delete_chunk(chunk_id)
    except Exception as e:
        error_logger.error(f'delete chunk : {chunk_id} error : {e}')
        error = OpenApiError(message="delete chunk failed",
                             body={"code": ApiReturn.CODE_INNER_CODE, "type": "delete_chunk_failed"})
        return HttpResponse(error.json_response(), status=500)
    return HttpResponse(ApiReturn(ApiReturn.CODE_OK, body={"chunk_id": chunk_id, "status": "success"}).to_json())


@require_http_methods(["POST"])
def update_chunk(request):
    data = json.loads(request.body)
    chunk_id = data.get('chunk_id')
    if not chunk_id:
        error = OpenApiError(message="require chunk_id",
                             body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)
    content_title = data.get('content_title')
    content_data = data.get('content_data')
    extra = data.get('extra')
    try:
        chunk_service.update_chunk(chunk_id, content_title, content_data, extra)
    except Exception as e:
        error_logger.error(f'update chunk : {chunk_id} error : {e}')
        error = OpenApiError(message="update chunk failed",
                             body={"code": ApiReturn.CODE_INNER_CODE, "type": "update_chunk_failed"})
        return HttpResponse(error.json_response(), status=500)
    return HttpResponse(ApiReturn(ApiReturn.CODE_OK, body={"chunk_id": chunk_id, "status": "success"}).to_json())


@require_http_methods(["POST"])
def chunk_list(request):
    data = json.loads(request.body)
    chunk_ids = data.get('chunk_ids')
    source_id = data.get('source_id')
    limit = data.get('limit', 10)
    offset = data.get('offset', 0)
    # 读强一致性
    read_strong_consistency = data.get('read_strong_consistency', False)
    if not chunk_ids and not source_id:
        error = OpenApiError(message="require chunk_ids or source_id",
                             body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)

    # chunk_ids是一个list，且不为空
    if chunk_ids and isinstance(chunk_ids, list) and len(chunk_ids) > 0:
        response = chunk_service.chunk_list_by_ids(chunk_ids)
    else:
        response = chunk_service.chunk_list_by_source_id(source_id, limit, offset, read_strong_consistency)
    return HttpResponse(ApiReturn(ApiReturn.CODE_OK, body={"chunk_list": response}).to_json())
