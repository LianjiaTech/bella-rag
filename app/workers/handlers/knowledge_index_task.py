import redis
from redis_lock import Lock

from app.common.contexts import TraceContext, ModelUsageRecord
from app.config.apollo_configs import file_access_config
from app.services.file_service import file_indexing
from common.tool.redis_tool import redis_pool
from init.settings import user_logger, DEFAULT_USER
from bella_rag.transformations.factory import TransformationFactory

logger = user_logger


def knowledge_index_task_callback(payload: dict) -> bool:
    file_id = payload.get('file_id')
    metadata = payload.get('metadata')
    file_name = payload.get('file_name')
    callbacks = payload.get('callbacks', [])
    user = payload.get('user', DEFAULT_USER)
    request_id = payload.get('request_id')

    lock = Lock(redis_client=redis.Redis(connection_pool=redis_pool),
                name=f"file_indexing_lock_{file_id}",
                auto_renewal=True,
                expire=180)
    try:
        lock.acquire()
        redis_client = redis.Redis(connection_pool=redis_pool)
        redis_key_prefix = "file_indexing_success_"

        has_done = redis_client.get(redis_key_prefix + file_id)
        if has_done:
            logger.info("已经消费完成，不需要再次消费 file_id = %s", file_id)
            return True

        # 使用用户上传文件的ak分摊成本
        ModelUsageRecord.usage_ak_code = payload.get('ak_code')
        ModelUsageRecord.usage_ak_sha = payload.get('ak_sha')
        TraceContext.trace_id = request_id
        metadata = metadata or {}
        file_indexing_black_list = file_access_config.file_space_black_list()
        # 根据文件space后缀加黑，先延缓大批量的文件上传攻击
        for black_space_id in file_indexing_black_list:
            if black_space_id in file_id:
                logger.info("blocked file indexing file_id = %s", file_id)
                return True

        # 获取业务Parser（如果有注册）,否则使用默认Parser
        custom_parsers = TransformationFactory.get_business_custom_parsers(
            csv={'file_id': file_id}
        )

        file_indexing(file_id=file_id, file_name=file_name,
                      metadata=metadata, callbacks=callbacks, user=user,
                      custom_parsers=custom_parsers)
        redis_client.setex(redis_key_prefix + file_id, 86400, "done")
    finally:
        if lock.locked():
            lock.release()
    return True
