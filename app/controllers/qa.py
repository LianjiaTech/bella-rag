import json
import uuid

from django.http import HttpResponse
from django.views.decorators.http import require_http_methods

from app.response.rag_response import OpenApiError
from app.services import qa_service
from common.helper import ApiReturn
from init.settings import error_logger


@require_http_methods(["POST"])
def add_qa_group(request):
    data = json.loads(request.body)
    source_id = data.get('source_id')
    source_name = data.get('source_name')
    questions = data.get('questions')
    answer = data.get('answer')
    extra = data.get('extra')
    if not source_id or not source_name or not questions or not answer:
        error = OpenApiError(message="require source_id, source_name, questions, answer",
                             body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)
    try:
        ids, group_id = qa_service.add_qa_group(source_id + "_" + str(uuid.uuid4()), source_id, source_name, questions,
                                                answer, extra)
    except Exception as e:
        error_logger.error(f'add_qa_group body : {json.dumps(data, ensure_ascii=False, indent=4)} error : {e}')
        error = OpenApiError(message="add qa group failed",
                             body={"code": ApiReturn.CODE_INNER_CODE, "type": "add_qa_group_failed"})
        return HttpResponse(error.json_response(), status=500)
    return HttpResponse(
        ApiReturn(ApiReturn.CODE_OK, body={"ids": ids, "group_id": group_id, "status": "success"}).to_json())


@require_http_methods(["POST"])
def delete_by_group_id(request):
    data = json.loads(request.body)
    group_id = data.get('group_id')
    if not group_id:
        error = OpenApiError(message="require group_id",
                             body={"code":  ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)
    try:
        qa_service.delete_qa_by_group_id(group_id)
    except Exception as e:
        error_logger.error(f'delete delete_by_group_id : {group_id} error : {e}')
        error = OpenApiError(message="delete qa by group id failed",
                             body={"code": ApiReturn.CODE_INNER_CODE, "type": "delete_qa_by_group_failed"})
        return HttpResponse(error.json_response(), status=500)
    return HttpResponse(ApiReturn(ApiReturn.CODE_OK, body={"group_id": group_id, "status": "success"}).to_json())


@require_http_methods(["POST"])
def coverage_group(request):
    data = json.loads(request.body)
    source_id = data.get('source_id')
    group_id = data.get('group_id')
    source_name = data.get('source_name')
    questions = data.get('questions')
    answer = data.get('answer')
    extra = data.get('extra')
    if not source_id or not source_name or not questions or not answer or not group_id:
        error = OpenApiError(message="require source_id, source_name, questions, answer, group_id",
                             body={"code":  ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)
    try:
        ids, group_id = qa_service.coverage_group(group_id, source_id, source_name, questions, answer, extra)
    except Exception as e:
        error_logger.error(f'coverage_group body : {json.dumps(data, ensure_ascii=False, indent=4)} error : {e}')
        error = OpenApiError(message="coverage group failed",
                             body={"code": ApiReturn.CODE_INNER_CODE, "type": "coverage_group_failed"})
        return HttpResponse(error.json_response(), status=500)
    return HttpResponse(
        ApiReturn(ApiReturn.CODE_OK, body={"ids": ids, "group_id": group_id, "status": "success"}).to_json())


@require_http_methods(["POST"])
def qa_list(request):
    data = json.loads(request.body)
    qa_ids = data.get('qa_ids')
    group_ids = data.get('group_ids')
    source_id = data.get('source_id')
    limit = data.get('limit', 10)
    offset = data.get('offset', 0)
    read_strong_consistency = data.get('read_strong_consistency', False)
    if not qa_ids and not group_ids and not source_id:
        error = OpenApiError(message="require qa_ids or group_ids or source_id",
                             body={"code":  ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
        return HttpResponse(error.json_response(), status=422)
    response = qa_service.qa_list(source_id=source_id, group_ids=group_ids, qa_ids=qa_ids, limit=limit, offset=offset,
                                  read_strong_consistency=read_strong_consistency)
    return HttpResponse(ApiReturn(ApiReturn.CODE_OK, body={"qa_list": response}).to_json())
