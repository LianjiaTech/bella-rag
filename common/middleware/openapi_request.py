import json
import re
import time

from bella_openapi.bella_trace import TRACE_ID
from bella_openapi.bella_trace._context import MOCK_REQUEST
from django.http import HttpResponse
from django.urls import resolve

from app import openapi_trace_handler as trace_handler
from app.common.contexts import UserContext, TraceContext, OpenapiContext
from app.response.rag_response import OpenApiError
from app.utils.metric_util import increment_counter
from init.settings import user_logger
from bella_rag.utils.openapi_util import valid_openapi_token

rag_path_patten = "^/api/rag/"
# 请求路径与trace step映射
rag_step_dict = {"/api/rag/query": "rag", "/api/rag/chat": "chat"}


class AuthorizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 解析当前请求的 URL 路由信息
        resolver_match = resolve(request.path)
        namespace = resolver_match.namespace  # 获取命名空间

        # 仅对 'app' 业务接口空间下的接口做鉴权
        if namespace == 'app':
            TraceContext.mock_request = request.headers.get(MOCK_REQUEST) or 'false'
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            OpenapiContext.ak = auth_header
            if not auth_header or not valid_openapi_token(auth_header):
                error = OpenApiError(message="ak is invalid",
                                     body={"code": "unauthorized", "type": "unauthorized"})
                return HttpResponse(error.json_response(), status=401)

        response = self.get_response(request)
        return response


class UserContextMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 指定需要拦截的接口路径
        protected_paths = ['/api/file/indexing', '/api/file/file_indexing_submit_task']

        if request.path in protected_paths or re.match(rag_path_patten, request.path):
            # 埋点流量计数
            increment_counter(request.path)
            data = json.loads(request.body)
            user = data.get("user")
            user_logger.info(f"request user info, path:{request.path}, user:{user}")
            if not user:
                error = OpenApiError(message="user must not be empty!",
                                     body={"code": "unauthorized", "type": "unauthorized"})
                return HttpResponse(error.json_response(), status=401)
            UserContext.user_id = user
            response = self.get_response(request)
            return response
        else:
            return self.get_response(request)


class RequestTraceMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if trace_id_h := request.headers.get(TRACE_ID):
            TraceContext.trace_id = trace_id_h
        else:
            TraceContext.trace_id = TraceContext.generate_trace_id()
        user_logger.info(f'{request.path} request trace id:{TraceContext.trace_id}')
        start = int(time.time() * 1000)
        response = self.get_response(request)
        if request.path in rag_step_dict and isinstance(response, HttpResponse):
            trace_args = [json.loads(request.body)]
            response_content = json.loads(response.content) if response.content else ''
            trace_handler.log_trace(rag_step_dict[request.path], TraceContext.trace_id,
                                    int(time.time() * 1000) - start, start,
                                    response_content, '', trace_args)
        return response
