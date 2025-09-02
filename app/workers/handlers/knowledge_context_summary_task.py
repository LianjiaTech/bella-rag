import redis

from app.common.contexts import UserContext, TraceContext
from init.settings import user_logger
from redis_lock import Lock

from common.tool.redis_tool import redis_pool
from bella_rag.transformations.extractor.extractors import ContextExtractor

logger = user_logger
context_extractor = ContextExtractor()

def knowledge_file_context_summary_callback(payload: dict) -> bool:
    file_id = payload.get('file_id')
    ucid = payload.get('ucid')
    extractors = payload.get('extractors', [])
    if context_extractor.type() not in extractors:
        return True

    lock = Lock(redis_client=redis.Redis(connection_pool=redis_pool),
                name=f"knowledge_file_context_summary_lock_{file_id}",
                auto_renewal=True,
                expire=180)
    try:
        lock.acquire()

        UserContext.user_id = ucid
        TraceContext.trace_id = file_id
        context_extractor.extract(source_id=file_id)
    finally:
        if lock.locked():
            lock.release()
    return True
