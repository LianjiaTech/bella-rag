from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from init.settings import error_logger
from common.helper.api import ApiReturn
import traceback
import sys
from common.helper.keones_exception import CodeError, CodeErrorForFe, CodeErrorNoData


class ExceptionMiddleware(MiddlewareMixin):

    def process_exception(self, request, exception):
        if isinstance(exception, CodeErrorForFe):
            return HttpResponse(ApiReturn(ApiReturn.CODE_ERROR_FOR_FE, str(exception.error_msg)).to_json())
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
