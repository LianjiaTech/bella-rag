import time

from llama_index.core.callbacks import CBEventType
from openai import RateLimitError

from app.utils.metric_util import histogram_with_buckets
from common.helper.exception import BusinessError
from init.settings import user_logger
from bella_rag import callback_manager

rag_histogram = histogram_with_buckets(
    'rag_step_cost',
    [0, 5000, 10000, 25000, 50000],
    ['step']
)


def trace(step, log_enabled=True, progress=''):
    """
    step: 原子步骤
    progress：阶段名，可以是多个step的集合
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            result = None  # 初始化 result 变量

            def send_event(status, message, **kwargs):
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
                # todo 此处有个坑，源码内部as_trace会清空callback_manager的上下文，导致出栈失败
                callback_manager.on_event_end(CBEventType.AGENT_STEP, payload)

            from app.common.contexts import TraceContext
            if progress:
                TraceContext.progress = progress

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
                send_event("success", '', **kwargs)
                return result
            except BusinessError as be:
                send_event("failed", be.error_msg)
                raise
            except RateLimitError as re:
                send_event("failed", str(re))
                raise
            except Exception as e:
                send_event("failed", 'Error: ' + str(e))
                raise

        return wrapper

    return decorator
