import json
import time
import traceback
from common.helper.api import ApiReturn, json_response
from common.tool.type_tool import TypeTool
from init.settings import *


def take_time(func):
    def take_time_wapper(*args, **kwargs):
        time_start = time.time()
        func_ret = func(*args, **kwargs)
        time_end = time.time()
        elapsed_ms = (time_end - time_start) * 1000
        if elapsed_ms > 5000:
            elapsed_logger.error("函数【%s】执行占用时间: %f ms" % (func.__module__ + "." + func.__name__, elapsed_ms))
        elif elapsed_ms > 1000:
            elapsed_logger.warning("函数【%s】执行占用时间: %f ms" % (func.__module__ + "." + func.__name__, elapsed_ms))
        elif elapsed_ms > 300:
            elapsed_logger.debug("函数【%s】执行占用时间: %f ms" % (func.__module__ + "." + func.__name__, elapsed_ms))
        else:
            elapsed_logger.info("函数【%s】执行占用时间: %f ms" % (func.__module__ + "." + func.__name__, elapsed_ms))
        return func_ret

    return take_time_wapper


def catch_exception(func):
    def catch_exception_wrapper(*args, **kwargs):
        try:
            func_ret = func(*args, **kwargs)
            return func_ret
        except Exception as e:
            ret_msg = "[EXCEPTION]: 函数【%s】异常：%s" % (func.__module__ + "." + func.__name__, e)
            error_logger.error(traceback.format_exc())
            error_logger.error(ret_msg)

    return catch_exception_wrapper


def validate_request_body_dict(func):
    def __deco(*args, **kwargs):
        request = args[0]
        reqbody = request.body.decode("utf8")
        if not TypeTool.is_dict_json_string(reqbody):
            return json_response(code=ApiReturn.CODE_BODY_INVALID_JSON_EXCEPTION, message='请求体必须是合法的json！')
        kwargs["body"] = json.loads(reqbody)
        return func(*args, **kwargs)
    return __deco
