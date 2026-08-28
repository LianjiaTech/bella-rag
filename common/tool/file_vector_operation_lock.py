from contextlib import contextmanager
import logging


FILE_VECTOR_LOCK_EXPIRE_SECONDS = 3600
FILE_VECTOR_LOCK_REDIS_TIMEOUT_SECONDS = 5
_file_vector_lock_redis_pool = None
logger = logging.getLogger(__name__)


def _file_vector_lock_redis_client():
    import redis

    from common.tool.redis_tool import redis_pool

    global _file_vector_lock_redis_pool
    if _file_vector_lock_redis_pool is None:
        connection_kwargs = dict(redis_pool.connection_kwargs)
        connection_kwargs.setdefault(
            'socket_connect_timeout',
            FILE_VECTOR_LOCK_REDIS_TIMEOUT_SECONDS,
        )
        connection_kwargs.setdefault(
            'socket_timeout',
            FILE_VECTOR_LOCK_REDIS_TIMEOUT_SECONDS,
        )
        _file_vector_lock_redis_pool = redis.ConnectionPool(
            **connection_kwargs,
        )
    return redis.Redis(connection_pool=_file_vector_lock_redis_pool)


@contextmanager
def file_vector_operation_lock(
        file_id: str,
        blocking: bool = False,
        timeout=None,
):
    """
    主 chunk 向量的最终互斥边界。

    索引、切片编辑、删除、归档和恢复会同时操作 MySQL 状态与外部向量库，
    数据库条件更新只能保护状态行，不能阻止外部副作用并发，因此必须共用同一文件锁。
    归档使用非阻塞获取并跳过忙文件；用户触发的写操作使用有限等待，超时后交给上游重试。
    """
    from redis_lock import Lock

    lock = Lock(
        redis_client=_file_vector_lock_redis_client(),
        name=f'file_vector_archive_lock_{file_id}',
        auto_renewal=True,
        expire=FILE_VECTOR_LOCK_EXPIRE_SECONDS,
    )
    acquired = False
    try:
        acquire_options = {'blocking': blocking}
        if blocking and timeout is not None:
            acquire_options['timeout'] = timeout
        acquired = lock.acquire(**acquire_options)
        yield acquired
    finally:
        if acquired:
            try:
                if lock.locked():
                    lock.release()
            except Exception as error:
                # 业务副作用此时可能已经完成。释放失败只记录告警并等待 TTL，
                # 不能用清理异常覆盖一个已经成功的索引、归档或删除结果。
                logger.warning(
                    f'释放文件向量操作锁失败: file_id={file_id}, error={error}'
                )
