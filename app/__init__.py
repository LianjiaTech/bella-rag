from app.callback.callback_handler import LlamaIndexTraceHandler, ProgressHandler, ExtractorHandler, \
    TraceRecordCallbackHandler
from bella_rag import callback_manager
import app.transformations

index_handler = LlamaIndexTraceHandler([], [])
progress_handler = ProgressHandler([], [])
extractor_handler = ExtractorHandler([], [])
openapi_trace_handler = TraceRecordCallbackHandler([], [])
callback_manager.add_handler(index_handler)
callback_manager.add_handler(progress_handler)
callback_manager.add_handler(extractor_handler)
callback_manager.add_handler(openapi_trace_handler)
