import contextvars
import json
import time
import traceback

from init.settings import trace_logger, user_logger


class RagEncoder(json.JSONEncoder):
    def default(self, obj):
        return str(obj)


logger = trace_logger
trace_context = contextvars.ContextVar("trace_id")

tag = 'rag_tag'


def trace_log(step):
    def decorator(func):
        def wrapper(*args, **kwargs):

            result = None
            start = int(time.time() * 1000)
            cost = 0
            try:
                result = func(*args, **kwargs)
                end = int(time.time() * 1000)
                cost = end - start
                log = build_trace_json(step, trace_context.get(), cost, start, result, None, *args, **kwargs)
                logger.info(log)
            except Exception:
                mg = traceback.format_exc()
                log = build_trace_json(step, trace_context.get(), cost, start, result, mg, *args, **kwargs)
                logger.info(log)
                raise
            return result

        return wrapper

    return decorator


def build_trace_json(step, trace_id, cost, start_time, result, error_msg, *args, **kwargs):
    log_json = None
    try:
        trace_log = dict()
        params = []
        for arg in args:
            params.append(arg)
        for item in kwargs.values():
            params.append(item)
        trace_log['operationLog'] = tag
        trace_log['nodeName'] = step
        trace_log['params'] = params
        trace_log['cost'] = cost
        trace_log['startTime'] = start_time
        trace_log['traceId'] = trace_id
        trace_log['result'] = result
        if error_msg:
            trace_log['errorCode'] = "500"
        else:
            trace_log['errorCode'] = "0"
        trace_log['errorMsg'] = error_msg
        trace_log['updateTime'] = start_time
        log_json = json.dumps(trace_log, cls=RagEncoder)
    except Exception:
        mg = traceback.format_exc()
        logger.info(mg)
    return log_json
