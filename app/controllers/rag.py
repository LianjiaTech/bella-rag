import json
import traceback

from django.http import HttpResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from openai import APIError

from app.common.contexts import TraceContext
from app.controllers import default_event_handler
from app.response.rag_response import OpenApiError, create_response
from app.runner import rag_runners
from app.services import rag_service
from app.strategy.retrieval import get_retrieval_mode_from_user_mode, build_plugins_from_user_mode
from app.utils.convert import convert_score_nodes_to_search_res
from app.utils.metric_util import increment_counter_with_tag
from app.controllers.request.request_validator import validate_request_params
from app.controllers.request.request_processor import extract_file_ids_from_scope
from common.helper import ApiReturn
from common.helper.exception import CheckError
from init.settings import user_logger, error_logger
from bella_rag.vector_stores.types import MetadataFilters


@require_http_methods(["POST"])
def search(request):
    try:
        # 获取参数
        data = json.loads(request.body)
        query = data.get('query')
        top_k = data.get('limit', 3)
        metadata_filters = MetadataFilters.from_dict(data.get('filter', {}))
        print(f'metadata_filters: {metadata_filters}')
        user_mode = data.get('mode', 'normal')

        # 参数验证
        if not query:
            error = OpenApiError(message="请求中query必传",
                                 body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
            return HttpResponse(error.json_response().encode('utf-8'), status=422)
        
        # 校验请求参数
        try:
            validate_request_params(data)
            scope = data.get('scope', [])
            file_ids = extract_file_ids_from_scope(scope)
        except CheckError as e:
            error = OpenApiError(message=e.error_msg,
                                 body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
            return HttpResponse(error.json_response().encode('utf-8'), status=422)

        # 直接使用用户模式获取检索配置
        retrieve_mode = get_retrieval_mode_from_user_mode(user_mode)
        plugins = build_plugins_from_user_mode(user_mode, top_k=top_k)
        
        nodes = rag_service.retrieval(file_ids=file_ids, query=query, top_k=int(top_k),
                                      score=0, metadata_filters=metadata_filters,
                                      retrieve_mode=retrieve_mode,
                                      plugins=plugins, )
        response = convert_score_nodes_to_search_res(nodes)
        return HttpResponse(json.dumps(create_response(0, "Success", response.to_dict()), ensure_ascii=False).encode('utf-8'))
    except CheckError as e:
        error = OpenApiError(message=e.error_msg,
                             body={"code": ApiReturn.CODE_PARAM_NOT_ALLOW, "type": "unsupported_params"})
        return HttpResponse(error.json_response().encode('utf-8'), status=422)
    except Exception as e:
        error_logger.exception(e)
        user_logger.error(f'retrieval request error :{str(e)}\\n{traceback.format_exc()}')
        # 添加接口error埋点
        increment_counter_with_tag('retrieval', 'error_code', e.__class__.__name__)
        error = OpenApiError(message=str(e),
                             body={"code": ApiReturn.CODE_INNER_CODE, "type": "internal_error"})
        return HttpResponse(error.json_response().encode('utf-8'), status=500)


@require_http_methods(["POST"])
def chat(request):
    try:
        # 获取请求的ak
        ak = request.META.get('HTTP_AUTHORIZATION', '')
        data = json.loads(request.body)
        # 生成参数
        model = data.get('model', 'c4ai-command-r-plus')
        show_quote = data.get('show_quote', False)

        # 检索参数
        top_k = data.get('limit', 3)
        metadata_filters = MetadataFilters.from_dict(data.get('filter', {}))

        # 用户模式参数处理
        user_mode = data.get('mode', 'normal')

        # 校验请求参数
        try:
            validate_request_params(data)
            scope = data.get('scope', [])
            file_ids = extract_file_ids_from_scope(scope)
            response_type = data.get('response_type', 'blocking')
        except CheckError as e:
            error = OpenApiError(message=e.error_msg,
                                 body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
            return HttpResponse(error.json_response().encode('utf-8'), status=422)

        # 直接使用用户模式获取检索配置
        retrieve_mode = get_retrieval_mode_from_user_mode(user_mode, top_k=top_k)
        plugins = build_plugins_from_user_mode(user_mode, top_k=top_k)

        # rag模式
        runner_class = rag_runners.get(user_mode, None)
        if runner_class is None:
            raise CheckError(f"不支持的模式：{user_mode}")

        # 初始化runner
        runner = runner_class(session_id=TraceContext.trace_id, event_handler=default_event_handler)
        
        # 用户提问
        query = data.get('query')
        if not query:
            error = OpenApiError(message="请求中query必传",
                                 body={"code": ApiReturn.CODE_BODY_PARAM_ERROR, "type": "param_error"})
            return HttpResponse(error.json_response().encode('utf-8'), status=422)
        if response_type == 'stream':
            r = StreamingHttpResponse(streaming_content=runner.rag_streaming(
                query=query, top_k=top_k, file_ids=file_ids, api_key=ak,
                model=model, metadata_filters=metadata_filters, retrieve_mode=retrieve_mode,
                plugins=plugins, show_quote=show_quote,
            ),
                content_type='text/event-stream')
            r['Cache-Control'] = 'no-cache'
            return r
        else:
            response = runner.rag(query=query, top_k=top_k, file_ids=file_ids, api_key=ak,
                                  model=model, metadata_filters=metadata_filters,
                                  retrieve_mode=retrieve_mode,
                                  plugins=plugins, show_quote=show_quote, )
            user_logger.info(f'rag response: {response}')
            return HttpResponse(json.dumps(create_response(0, "Success", response), ensure_ascii=False).encode('utf-8'), status=200)
    except json.JSONDecodeError:
        user_logger.error('rag request error :Invalid JSON')
        error = OpenApiError(message="Invalid JSON",
                             body={"code": ApiReturn.CODE_BODY_INVALID_JSON_EXCEPTION, "type": "invalid_json"})
        return HttpResponse(error.json_response().encode('utf-8'), status=422)
    except CheckError as e:
        error = OpenApiError(message=e.error_msg,
                             body={"code": ApiReturn.CODE_PARAM_NOT_ALLOW, "type": "unsupported_params"})
        return HttpResponse(error.json_response().encode('utf-8'), status=422)
    except APIError as e:
        increment_counter_with_tag('rag', 'error_code', e.code)
        user_logger.error(f'rag open api error: {str(e)}\n{traceback.format_exc()}')
        return HttpResponse(json.dumps(e.body, ensure_ascii=False), status=int(e.code))
    except Exception as e:
        user_logger.error(f'rag chat request error :{str(e)}\n{traceback.format_exc()}')
        increment_counter_with_tag('rag', 'error_code', e.__class__.__name__)
        error = OpenApiError(message=str(e),
                             body={"code": ApiReturn.CODE_INNER_CODE, "type": "internal_error"})
        return HttpResponse(error.json_response().encode('utf-8'), status=500)
