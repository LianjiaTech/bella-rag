import requests

from app.common.contexts import TraceContext
from common.helper.exception import BusinessError
from init.settings import user_logger
from bella_rag.callbacks.manager import get_callbacks
from bella_rag.utils.file_api_tool import file_api_client


def report_callbacks(func_name: str, e: Exception):
    trace_id = TraceContext.trace_id
    if trace_id:
        if isinstance(e, BusinessError):
            err_message = e.error_msg
        else:
            err_message = 'internal error'
        # 上报file api
        file_api_client.update_processing_status('failed', 0, trace_id, err_message,  TraceContext.progress)
        # 通知回调
        callbacks = get_callbacks()
        for callback in callbacks:
            try:
                requests.post(callback, json={'step': func_name, 'status': 'failed',
                                              'trace_id': trace_id, 'message': err_message})
            except Exception as e:
                user_logger.error(f'{trace_id} report_exception error in {callback}: {e}')
