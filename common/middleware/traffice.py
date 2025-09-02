from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from init.settings import error_logger, traffic_logger
from common.helper.api import ApiReturn
import traceback
from common.tool.common_func import *
import time
import random
import json
import sys
from common.helper.exception import CodeError, CodeErrorForFe, CodeErrorNoData


class TrafficMiddleware(MiddlewareMixin):
    @staticmethod
    def traffic_log(request, response):
        try:
            request_body = request.body.decode("utf8")
        except:
            try:
                request_body = str(request.body) if request.body else ""
            except:
                request_body = "@@@@@@@@@@@@@@@@@@@@stream@@@@@@@@@@@@@@@@@@@"
        try:
            response_text = response.content.decode("utf8")
        except:
            try:
                response_text = str(response.content) if response.content else ""
            except:
                response_text = "@@@@@@@@@@@@@@@@@@@@stream@@@@@@@@@@@@@@@@@@@"
        max_respones_size = int(1024 * 1024 * 1.5)
        # max_respones_size = 10
        output_response_text = response_text if len(response_text) <= max_respones_size \
            else response_text[:max_respones_size]

        HTTP_SIGN = request.META.get("HTTP_SIGN")
        HTTP_TIMESTAMP = request.META.get("HTTP_TIMESTAMP")
        HTTP_TOKEN = request.META.get("HTTP_TOKEN")
        HTTP_APPKEY = request.META.get("HTTP_APPKEY")
        request_source = "UNKNOWN"
        request_appkey = ""
        if HTTP_SIGN and HTTP_TIMESTAMP:
            request_source = "SIGN"
        elif HTTP_TOKEN and HTTP_APPKEY:
            request_source = "TOKEN"
            request_appkey = HTTP_APPKEY

        traffic_dict = {
            "traceId": request.META['HTTP_TRACEID'],
            "current_time": get_current_time(),
            "user": request.META.get('HTTP_EMAIL_PREFIX', ""),
            "scheme": request.scheme,
            "request_method": request.method,
            "request_url": request.path,
            "request_path_info": request.META.get('QUERY_STRING', ""),
            "request_body": request_body,
            "response_text": output_response_text,
            "elapsed": (time.time() - float(request.META.get("START_TIMESTAMP", 0.0))),
            "request_source": request_source,
            "request_appkey": request_appkey,
        }
        traffic_logger.info(json.dumps(traffic_dict, ensure_ascii=False))

    def process_request(self, request):
        if "HTTP_TRACEID" not in request.META.keys():
            request.META['HTTP_TRACEID'] = "%s-%s" % (time.time(),
                                                      md5(get_current_time() + str(random.randint(0, 9999999999))))
            request.META["START_TIMESTAMP"] = time.time()

    def process_view(self, request, view_func, *args, **kwargs):
        pass

    def process_response(self, request, response):
        # 处理404响应
        if isinstance(response, HttpResponse):
            if response.status_code == 404:
                msg = "%s 不合法的url！" % request.path
                response.content = ApiReturn(ApiReturn.CODE_URL_NOT_FOUND, msg).to_json().encode("utf8")
        # 给response增加TRACEID
        response['START_TIMESTAMP'] = request.META.get("START_TIMESTAMP")
        response['TRACEID'] = request.META.get("HTTP_TRACEID")
        # 打印日志
        TrafficMiddleware.traffic_log(request, response)
        try:
            # loads成功说明是json
            json.loads(response.content.decode("utf8"))
            response["Content-Type"] = "application/json"
        except:
            # 出现异常说明不是json, 不需要修改头信息
            pass
        response['END_TIMESTAMP'] = time.time()
        response['ELAPSED'] = str(float(response['END_TIMESTAMP']) - float(response['START_TIMESTAMP']))
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, CodeErrorForFe):
            return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR_FOR, str(exception.error_msg)).to_json())
        elif isinstance(exception, CodeError):
            return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR, str(exception.error_msg)).to_json())
        elif isinstance(exception, CodeErrorNoData):
            return HttpResponse(ApiReturn(ApiReturn.CODE_NO_DATA, str(exception.error_msg)).to_json())
        else:
            error_logger.error(
                "URL[%s]:traceId[%s]:\n%s" % (request.path_info, request.META.get("HTTP_TRACEID"),
                                              traceback.format_exc()))
            sys.stdout.flush()  # 刷新缓冲区
            return HttpResponse(ApiReturn(ApiReturn.CODE_REQUEST_EXCEPTION,
                                          "[%s]%s" % (request.META.get("HTTP_TRACEID"), str(exception))).to_json())
