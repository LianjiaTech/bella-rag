def ensure_tencent_delete_succeeded(delete_result) -> int:
    """校验腾讯向量库删除响应，并返回受影响记录数。"""
    if not delete_result or delete_result.get('code', -1) != 0:
        raise RuntimeError(
            f'delete data from tencent vectordb failed: {delete_result}',
        )
    affected_count = delete_result.get('affectedCount')
    if isinstance(affected_count, bool) or not isinstance(affected_count, int) or affected_count < 0:
        raise RuntimeError(
            f'invalid affectedCount in tencent vectordb delete result: {delete_result}',
        )
    return affected_count


def delete_tencent_in_batches(delete_call, tencent_filter, batch_limit: int = 15000) -> None:
    """分批删除腾讯向量库数据，任意一批失败都向上抛出。"""
    while True:
        delete_result = delete_call(filter=tencent_filter, limit=batch_limit)
        affected_count = ensure_tencent_delete_succeeded(delete_result)
        if affected_count < batch_limit:
            return
