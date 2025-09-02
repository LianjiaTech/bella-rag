from typing import List

from django.db import transaction

from app.models.chunk_content_attached_model import ChunkContentAttached, ChunkContentAttachedMapper
from init.settings import user_logger


class ChunkContentAttachedService:
    """
    因为数据安全问题腾讯向量库不允许保存content，所以增加此Service辅助向量化保存结果
    """

    @staticmethod
    def source_has_exist(source_id: str):
        ChunkContentAttachedMapper.source_has_exist(source_id=source_id)

    @staticmethod
    @transaction.atomic
    def batch_save(chunk_content_attached_list: List[ChunkContentAttached], batch_size: int = 500, connection=None):
        total = len(chunk_content_attached_list)
        user_logger.info(f"start save batch chunks, size : {total}")
        for index in range(0, total, batch_size):
            batch_list = chunk_content_attached_list[index:index + batch_size]
            ChunkContentAttachedMapper.batch_save(chunk_content_attached_list=batch_list, connection=connection)

    @staticmethod
    def save(chunk_content_attached: ChunkContentAttached):
        ChunkContentAttachedMapper.save(chunk_content_attached=chunk_content_attached)

    @staticmethod
    def get_by_chunk_id(chunk_id: str) -> ChunkContentAttached:
        return ChunkContentAttachedMapper.get_by_chunk_id(chunk_id=chunk_id)

    @staticmethod
    def batch_get_by_chunk_ids(chunk_ids: List[str]) -> List[ChunkContentAttached]:
        return ChunkContentAttachedMapper.batch_get_by_chunk_ids(chunk_ids=chunk_ids)

    @staticmethod
    async def async_batch_get_by_chunk_ids(chunk_ids: List[str]):
        yield await ChunkContentAttachedMapper.batch_get_by_chunk_ids_async(chunk_ids)

    @staticmethod
    def delete_by_chunk_id(chunk_id: int):
        return ChunkContentAttachedMapper.delete_by_chunk_id(chunk_id=chunk_id)

    @staticmethod
    def delete_by_chunk_ids(chunk_ids: List[str]):
        return ChunkContentAttachedMapper.delete_by_chunk_ids(chunk_ids=chunk_ids)

    @staticmethod
    def chunk_pos_increment(source_id: str, index: int):
        ChunkContentAttachedMapper.chunk_pos_increment(source_id=source_id, index=index)

    @staticmethod
    def chunk_pos_decrement(source_id: str, index: int):
        ChunkContentAttachedMapper.chunk_pos_decrement(source_id=source_id, index=index)

    @staticmethod
    def find_max_id_pos(source_id: str) -> int:
        max_id_chunk = ChunkContentAttachedMapper.find_max_id_chunk(source_id=source_id)
        if max_id_chunk is None:
            return -1
        return int(max_id_chunk.chunk_id.split('-')[-1])

    @staticmethod
    def update_chunks_token(source_id: str, changed_order_num: str, token_diff: int) -> None:
        """
        某节点内容更新后，更新所有父节点token量
        """
        if changed_order_num and source_id:
            user_logger.info(f'update_chunks_token order num:{changed_order_num}, token diff:{token_diff}')
            parts = changed_order_num.split('.')
            parent_order_nums = ['.'.join(parts[:i]) for i in range(1, len(parts) + 1)]
            ChunkContentAttachedMapper.chunk_token_update(source_id=source_id, order_nums=parent_order_nums,
                                                          token_diff=token_diff)

    @staticmethod
    def delete_by_source_id(source_id: str):
        return ChunkContentAttachedMapper.delete_by_source_id(source_id=source_id)

    @staticmethod
    def batch_get_by_source_id(source_id: str, limit: int, offset: int):
        return ChunkContentAttachedMapper.batch_get_by_source_id(source_id, limit, offset)

    @staticmethod
    def get_all_chunks_by_source_id(source_id: str) -> List[ChunkContentAttached]:
        all_chunks = []
        limit = 500
        offset = 0

        while True:
            chunks = ChunkContentAttachedMapper.batch_get_by_source_id(source_id, limit, offset)
            if not chunks:
                break
            all_chunks.extend(chunks)
            offset += limit

        return all_chunks

    @staticmethod
    def find_structure_node(source_id: str, limit: int, offset: int) -> List[ChunkContentAttached]:
        return ChunkContentAttachedMapper.search_structure_nodes(source_id, limit, offset)

    @staticmethod
    def update_chunks_context_id(chunk_ids: List[str], context_id: str):
        ChunkContentAttachedMapper.update_chunks_context_id(chunk_ids, context_id)

    @staticmethod
    def get_all_chunks_by_context_id(context_id: str) -> List[ChunkContentAttached]:
        all_chunks = []
        limit = 500
        offset = 0

        while True:
            chunks = ChunkContentAttachedMapper.batch_get_by_context_id(context_id, limit, offset)
            if not chunks:
                break
            all_chunks.extend(chunks)
            offset += limit

        return all_chunks

    @staticmethod
    def get_distinct_context_ids_by_source_id(source_id: str) -> List[str]:
        return ChunkContentAttachedMapper.get_distinct_context_ids_by_source_id(source_id)

    @staticmethod
    def update_source_context_id(source_id: str, context_id: str):
        ChunkContentAttachedMapper.update_source_context_id(source_id, context_id)
