import json

from django.http import HttpResponse
from django.views.decorators.http import require_http_methods

from app.common.contexts import TraceContext
from app.response.rag_response import OpenApiError
from app.services import file_service
from app.services.file_service import async_file_indexing, rename_file
from app.workers import knowledge_index_task_kafka_producer
from app.workers.producers.producers import async_send_kafka_message
from common.helper import ApiReturn
from common.helper.exception import CheckError
from init.settings import user_logger, error_logger
from bella_rag.utils.file_util import get_file_name
from bella_rag.utils.user_util import get_user_info


@require_http_methods(["POST"])
def file_indexing(request):
    try:
        data = json.loads(request.body)
        # 获取参数
        file_id = data.get('file_id')
        file_name = data.get('file_name', '')
        callback = data.get('callback')
        metadata = data.get('metadata', {})
        if not file_id:
            raise CheckError("请求体中file_id必传")
        async_file_indexing(file_id=file_id, file_name=file_name,
                            metadata=metadata, callbacks=[callback], user=get_user_info())
        return HttpResponse(ApiReturn(ApiReturn.CODE_OK, body={"file_id": file_id, "status": "success"}).to_json())
    except CheckError as e:
        error = OpenApiError(message=e.error_msg,
                             body={"code": ApiReturn.CODE_INNER_CODE, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)
    except json.JSONDecodeError:
        error = OpenApiError(message="Invalid JSON",
                             body={"code": ApiReturn.CODE_BODY_INVALID_JSON_EXCEPTION, "type": "invalid_json"})
        return HttpResponse(error.json_response(), status=422)


@require_http_methods(["POST"])
def file_stream_indexing(request):
    try:
        file_id = request.POST.get("file_id")
        file_name = request.POST.get("file_name")
        user = request.POST.get("user")
        metadata = json.loads(request.POST.get("metadata", "{}"))

        file_obj = request.FILES.get("file")
        if not file_obj:
            raise CheckError("必须上传文件流！")

        if not file_id:
            raise CheckError("file_id为必传！")

        user_logger.info(f'start indexing file from stream: {file_id}')
        file_service.file_stream_indexing(
            file_id=file_id,
            file_name=file_name,
            file_stream=file_obj.file,
            metadata=metadata,
            user=user,
        )

        return HttpResponse(ApiReturn(ApiReturn.CODE_OK, body={"file_id": file_id, "status": "success"}).to_json())
    except CheckError as e:
        error = OpenApiError(message=e.error_msg,
                             body={"code": ApiReturn.CODE_INNER_CODE, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)
    except Exception as e:
        error_logger.error(f'file index from stream failed : {file_id} error : {e}')
        error = OpenApiError(message="file stream indexing failed",
                             body={"code": ApiReturn.CODE_INNER_CODE, "type": "file_indexing_failed"})
        return HttpResponse(error.json_response(), status=500)


@require_http_methods(["POST"])
def file_indexing_submit_task(request):
    try:
        data = json.loads(request.body)
        # 获取参数
        file_id = data.get('file_id')
        file_path = data.get('file_path')
        try:
            data["request_id"] = TraceContext.trace_id
            data["file_name"] = get_file_name(file_path)
        except Exception:
            user_logger.info('file_indexing_submit_task request id not found')
        if not file_id:
            error = OpenApiError(message="请求体中file_id必传",
                                 body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
            return HttpResponse(error.json_response(), status=422)
        if not file_path:
            error = OpenApiError(message="请求体中file_path必传",
                                 body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
            return HttpResponse(error.json_response(), status=422)
        send_result = async_send_kafka_message(knowledge_index_task_kafka_producer, json.dumps(data))
        if send_result:
            return HttpResponse(ApiReturn(ApiReturn.CODE_OK, body={"file_id": file_id, "status": "success"}).to_json())
        else:
            return HttpResponse(
                ApiReturn(ApiReturn.CODE_CREATE_FILE_INDEXING_ERROR,
                          body={"code": ApiReturn.CODE_CREATE_FILE_INDEXING_ERROR,
                                "type": "create file_indexing task failure"}))
    except CheckError as e:
        error = OpenApiError(message=e.error_msg,
                             body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)
    except json.JSONDecodeError:
        error = OpenApiError(message="Invalid JSON",
                             body={"code": ApiReturn.CODE_BODY_INVALID_JSON_EXCEPTION, "type": "invalid_json"})
        return HttpResponse(error.json_response(), status=422)


@require_http_methods(["POST"])
def file_delete_submit_task(request):
    data = json.loads(request.body)
    file_id = data.get('file_id')
    if not file_id:
        error = OpenApiError(message='require file_id in request',
                             body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)
    try:
        send_result = file_service.file_delete_submit_task(file_id=file_id)
        if send_result:
            return HttpResponse(ApiReturn(ApiReturn.CODE_OK, body={"file_id": file_id, "status": "success"}).to_json())
        else:
            return HttpResponse(
                ApiReturn(ApiReturn.CODE_DELETE_FILE_INDEXING_ERROR,
                          body={"file_id": file_id, "status": "create file_delete task failure"}).to_json())
    except Exception as e:
        error_logger.error(f'delete file : {file_id} error : {e}')
        error = OpenApiError(message="delete file failed",
                             body={"code": ApiReturn.CODE_DELETE_FILE_INDEXING_ERROR, "type": "file_delete_failed"})
        return HttpResponse(error.json_response(), status=500)


@require_http_methods(["POST"])
def file_rename(request):
    data = json.loads(request.body)
    file_id = data.get('file_id')
    file_name = data.get('file_name')
    if not file_id:
        error = OpenApiError(message='require file_id in request',
                             body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)
    if not file_name:
        error = OpenApiError(message="require file_name",
                             body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)
    try:
        rename_file(file_id=file_id, file_name=file_name)
    except Exception as e:
        error_logger.error(f'rename file : {file_id} error : {e}')
        error = OpenApiError(message="rename file failed",
                             body={"code": ApiReturn.CODE_INNER_CODE, "type": "file_rename_failed"})
        return HttpResponse(error.json_response(), status=500)
    return HttpResponse(ApiReturn(ApiReturn.CODE_OK, body={"file_id": file_id, "status": "success"}).to_json())


@require_http_methods(["POST"])
def file_update(request):
    data = json.loads(request.body)
    source_id = data.get('source_id')
    if not source_id:
        error = OpenApiError(message="require source_id",
                             body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)
    extra = data.get('extra')
    try:
        file_service.file_update(source_id, extra)
    except Exception as e:
        error_logger.error(f'batch_update chunk : {source_id} error : {e}')
        error = OpenApiError(message="batch_update chunk failed",
                             body={"code": ApiReturn.CODE_INNER_CODE, "type": "batch_update_chunk_failed"})
        return HttpResponse(error.json_response(), status=500)
    return HttpResponse(ApiReturn(ApiReturn.CODE_OK, body={"source_id": source_id, "status": "success"}).to_json())


@require_http_methods(["POST"])
def file_summary_query(request):
    user_logger.info(f'file_summary_query request:{request.body.decode("utf-8")}')
    data = json.loads(request.body)
    file_ids = data.get('file_ids', [])
    query = data.get('query', len(file_ids))
    if not query:
        error = OpenApiError(message="require query",
                             body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)
    if not file_ids:
        error = OpenApiError(message="file_ids must not be empty",
                             body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)
    top_k = data.get('top_k', len(file_ids))
    try:
        res = file_service.get_file_summary(file_ids=file_ids, top_k=top_k, query=query)
        return HttpResponse(ApiReturn(ApiReturn.CODE_OK, body=res).to_json())
    except Exception as e:
        error = OpenApiError(message=str(e),
                             body={"code": ApiReturn.CODE_INNER_CODE, "type": "internal_error"})
        return HttpResponse(json.dumps(error), status=500)


@require_http_methods(["POST"])
def file_summaries(request):
    user_logger.info(f'file_summary request:{request.body.decode("utf-8")}')
    data = json.loads(request.body)
    file_ids = data.get('file_ids', [])
    if not file_ids:
        error = OpenApiError(message="file_ids must not be empty",
                             body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)
    try:
        res = file_service.get_file_summaries(file_ids=file_ids)
        return HttpResponse(ApiReturn(ApiReturn.CODE_OK, body=res).to_json())
    except Exception as e:
        error = OpenApiError(message=str(e),
                             body={"code": ApiReturn.CODE_INNER_CODE, "type": "internal_error"})
        return HttpResponse(json.dumps(error), status=500)
