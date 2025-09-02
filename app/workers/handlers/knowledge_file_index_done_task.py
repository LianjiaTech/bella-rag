import redis
from redis_lock import Lock

from app.common.contexts import UserContext
from common.helper.exception import FileNotFoundException
from common.tool.redis_tool import redis_pool
from init.settings import user_logger
from bella_rag.transformations.extractor.extractors import SummaryQuestionExtractor, EXTRACTOR_SUMMARY

logger = user_logger
summary_extractors = [SummaryQuestionExtractor()]


def knowledge_file_summary_extract_callback(payload: dict) -> bool:
    file_id = payload.get('file_id')
    file_name = payload.get('file_name')
    ucid = payload.get('ucid')
    extractors = payload.get('extractors', [])

    lock = Lock(redis_client=redis.Redis(connection_pool=redis_pool),
                name=f"knowledge_file_index_done_task_lock_{file_id}",
                auto_renewal=True,
                expire=180)
    try:
        lock.acquire()
        redis_client = redis.Redis(connection_pool=redis_pool)
        redis_key_prefix = "file_indexing_done_callback_success_"

        has_done = redis_client.get(redis_key_prefix + file_id)
        if has_done:
            logger.info("已经消费完成，不需要再次消费 file_id = %s", file_id)
            return True
        UserContext.user_id = ucid
        for extractor in summary_extractors:
            if extractor.type() in extractors:
                # summary分别提取
                extractor.extract(file_id, source_name=file_name)

        redis_client.setex(redis_key_prefix + file_id, 86400, "done")
    except FileNotFoundException:
        logger.warn(f'file summary extract failed, file not found : {file_id}')
        return True
    finally:
        if lock.locked():
            lock.release()
    return True
