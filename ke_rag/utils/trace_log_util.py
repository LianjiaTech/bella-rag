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
                rag_histogram.labels(step).observe(cost)
                user_logger.info(f'rag step : {step} time cost : {cost}')
                payload = {
                    "step": step,
                    "status": status,
                    "trace_id": trace_id,
                    "message": message,
                    "cost": cost,
                    "result": result,
                    "log_enabled": log_enabled,
                    "args": args,
                    "kwargs": kwargs
                }
                # event不支持自定义，在payload传递真正的step
                callback_manager.on_event_end(CBEventType.AGENT_STEP, payload)

            start = int(time.time() * 1000)
            trace_id = TraceContext.trace_id
            if not trace_id:
                # 上下文找不到trace_id则直接返回
                res = func(*args, **kwargs)
                rag_histogram.labels(step).observe(int(time.time() * 1000) - start)
                user_logger.info(f'rag step : {step} time cost : {int(time.time() * 1000) - start}')
                return res

            try:
                user_logger.info(f"trace step:{step}, trace id:{trace_id}")
                callback_manager.on_event_start(CBEventType.AGENT_STEP, {"step": step, "trace_id": trace_id})
                result = func(*args, **kwargs)
                send_event("success", '', **kwargs, result=result)
                return result
            except BusinessError as be:
                send_event("failed", be.error_msg)
                raise
            except Exception:
                send_event("failed", "internal error")
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
