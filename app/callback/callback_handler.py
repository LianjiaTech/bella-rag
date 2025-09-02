import json
import re
import traceback
from typing import Dict, Optional, List, Any, Set

import requests
from llama_index.core import BaseCallbackHandler
from llama_index.core.callbacks import CBEventType
from tqdm import tqdm

from app.common.contexts import TraceContext
from init.settings import trace_logger
from init.settings import user_logger
from bella_rag.callbacks.manager import get_callbacks
from bella_rag.utils.file_api_tool import file_api_client


class RagEncoder(json.JSONEncoder):
    def default(self, obj):
        return str(obj)


class ProgressHandler(BaseCallbackHandler):
    file_index_progress_rate_map: Dict[str, float] = {
        'read_file': 0.1,
        '.*_parse': 0.4,
        'build_recall_index': 0.6,
        'generate_embeddings': 0.8,
        'multi_index_construction': 1,
    }

    def on_event_start(self,
                       event_type: CBEventType,
                       payload: Optional[Dict[str, Any]] = None,
                       event_id: str = "",
                       parent_id: str = "",
                       **kwargs: Any):
        user_logger.info(f'ProgressHandler on_event_start : {event_id}')

    def on_event_end(self,
                     event_type: CBEventType,
                     payload: Optional[Dict[str, Any]] = None,
                     event_id: str = "",
                     parent_id: str = "",
                     **kwargs: Any):
        if payload and payload.get('step'):
            step = payload.get('step')
            status = payload.get('status')
            trace_id = payload.get('trace_id')
            message = payload.get('message', '')

            # 默认进度为0
            progress = 0
            matched = False
            # 遍历所有阶段，检查是否匹配
            for pattern, rate in self.file_index_progress_rate_map.items():
                if re.match(pattern, step):
                    progress = rate
                    matched = True
                    break

            if not matched:
                return

            if status == 'success':
                # 设置进度条
                progress = int(progress * 100)
                bar = tqdm(total=100, desc=f'[trace:{trace_id} step:{step}]阶段完成, RAG Progress', position=0,
                           leave=True)
                bar.update(progress)
                file_api_client.update_processing_status(step, progress, trace_id, message, TraceContext.progress)

            if status == 'failed':
                file_api_client.update_processing_status('failed', 0, trace_id, message, TraceContext.progress)

    def start_trace(self, trace_id: Optional[str] = None) -> None:
        user_logger.info(f'ProgressHandler start_trace : {trace_id}')

    def end_trace(self,
                  trace_id: Optional[str] = None,
                  trace_map: Optional[Dict[str, List[str]]] = None):
        user_logger.info(f'ProgressHandler start_trace : {trace_id}')


class ExtractorHandler(BaseCallbackHandler):
    """
    后置处理器处理状态上报
    """
    extractor_steps: Set[str] = {
        'context_summary', 'summary_question',
    }

    def on_event_start(self,
                       event_type: CBEventType,
                       payload: Optional[Dict[str, Any]] = None,
                       event_id: str = "",
                       parent_id: str = "",
                       **kwargs: Any):
        user_logger.info(f'ExtractorHandler on_event_start : {event_id}')

    def on_event_end(self,
                     event_type: CBEventType,
                     payload: Optional[Dict[str, Any]] = None,
                     event_id: str = "",
                     parent_id: str = "",
                     **kwargs: Any):
        if payload and payload.get('step'):
            step = payload.get('step')
            status = payload.get('status')
            trace_id = payload.get('trace_id')
            message = payload.get('message', '')

            if step not in self.extractor_steps:
                return

            if status == 'success':
                bar = tqdm(total=100, desc=f'[trace:{trace_id} step:{step}]阶段完成, RAG Progress', position=0,
                           leave=True)
                bar.update(100)
                file_api_client.update_processing_status(step, 100, trace_id, message, TraceContext.progress)

            if status == 'failed':
                file_api_client.update_processing_status('failed', 0, trace_id, message, TraceContext.progress)

    def start_trace(self, trace_id: Optional[str] = None) -> None:
        user_logger.info(f'ExtractorHandler start_trace : {trace_id}')

    def end_trace(self,
                  trace_id: Optional[str] = None,
                  trace_map: Optional[Dict[str, List[str]]] = None):
        user_logger.info(f'ExtractorHandler start_trace : {trace_id}')


class LlamaIndexTraceHandler(BaseCallbackHandler):
    """
    进度回调处理器
    """

    def on_event_start(self,
                       event_type: CBEventType,
                       payload: Optional[Dict[str, Any]] = None,
                       event_id: str = "",
                       parent_id: str = "",
                       **kwargs: Any):
        if payload.get('step'):
            user_logger.info(f'{payload.get("step")} started.')

    def on_event_end(self,
                     event_type: CBEventType,
                     payload: Optional[Dict[str, Any]] = None,
                     event_id: str = "",
                     parent_id: str = "",
                     **kwargs: Any):
        if payload and payload.get('step'):
            step = payload.get('step')
            status = payload.get('status')
            trace_id = payload.get('trace_id')
            message = payload.get('message', '')
            callbacks = get_callbacks()
            user_logger.info(f"rag_signal_callback: {step}, {status}, {trace_id}, {callbacks}, {message}")
            for callback in callbacks:
                # do callback
                try:
                    requests.post(callback, json={'step': step, 'status': status,
                                                  'trace_id': trace_id, 'message': message})
                except Exception as e:
                    user_logger.error(f'{trace_id} rag_signal_callback error in {callback}: {e}')

    def start_trace(self, trace_id: Optional[str] = None) -> None:
        user_logger.info(f'{trace_id} started.')

    def end_trace(self,
                  trace_id: Optional[str] = None,
                  trace_map: Optional[Dict[str, List[str]]] = None):
        # 这里承接llama-index框架内的trace定义，例如index-contruction
        step = trace_id
        status = 'success'
        trace_id = TraceContext.trace_id
        callbacks = get_callbacks()
        user_logger.info(f'{trace_id} step {step} end.')
        for callback in callbacks:
            # do callback
            try:
                requests.post(callback, json={'step': step, 'status': status, 'trace_id': trace_id})
            except Exception as e:
                user_logger.error(f'{trace_id} rag_signal_callback error in {callback}: {e}')


class TraceRecordCallbackHandler(BaseCallbackHandler):
    """
    打印trace日志
    """

    def on_event_start(self,
                       event_type: CBEventType,
                       payload: Optional[Dict[str, Any]] = None,
                       event_id: str = "",
                       parent_id: str = "",
                       **kwargs: Any):
        """
        事件开始回调
        """
        pass

    def on_event_end(self,
                     event_type: CBEventType,
                     payload: Optional[Dict[str, Any]] = None,
                     event_id: str = "",
                     parent_id: str = "",
                     **kwargs: Any):

        if payload and payload.get('step'):
            log_enabled = payload.get('log_enabled', False)
            if log_enabled:
                step = payload.get('step')
                trace_id = payload.get('trace_id')
                # 打印trace日志
                self.log_trace(step, trace_id,
                               payload.get('cost', 0), payload.get('start', 0), payload.get('result'),
                               payload.get('message', ''), payload.get('args', []), payload.get('kwargs', {}))

    def start_trace(self, trace_id: Optional[str] = None) -> None:
        """
        追踪开始回调
        """
        pass

    def end_trace(self,
                  trace_id: Optional[str] = None,
                  trace_map: Optional[Dict[str, List[str]]] = None):
        """
        追踪结束回调
        """
        pass

    def log_trace(self, step, trace_id, cost, start_time, result, error_msg, *args, **kwargs):
        try:
            trace_log = dict()
            params = []
            for arg in args:
                params.append(arg)
            for item in kwargs.values():
                params.append(item)
            trace_log['step'] = step
            trace_log['params'] = params
            trace_log['cost'] = cost
            trace_log['data_info_msg_bellaTraceId'] = trace_id
            trace_log['result'] = result
            trace_log['errorCode'] = "500" if error_msg else "0"
            trace_log['loglevel'] = "ERROR" if error_msg else "INFO"
            trace_log['errorMsg'] = error_msg
            trace_log['timestamp'] = start_time
            log_json = json.dumps(trace_log, cls=RagEncoder, ensure_ascii=False)
            trace_logger.info(log_json)
        except Exception:
            mg = traceback.format_exc()
            trace_logger.info(mg)
