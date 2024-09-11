from typing import List

from django.db import transaction

from app.models.chunk_question_attached_model import ChunkQuestionAttached, ChunkQuestionAttachedMapper


class ChunkQuestionAttachedService:
    """
    因为数据安全问题腾讯向量库不允许保存content，所以增加此Service辅助向量化保存结果
    """

    @staticmethod
    @transaction.atomic
    def coverage_data(chunk_question_attached_list: List[ChunkQuestionAttached]):
        """覆盖数据：先删除后插入，在事务里，用户只能感知最后结果"""
        if not chunk_question_attached_list:
            return
        distinct_chunk_ids = {chunk_question_attached.chunk_id for chunk_question_attached in
                              chunk_question_attached_list}
        ChunkQuestionAttachedMapper.delete_by_chunk_ids(distinct_chunk_ids)
        ChunkQuestionAttachedMapper.batch_save(chunk_question_attached_list)
        object_ids = ChunkQuestionAttached.objects.filter(chunk_id__in=distinct_chunk_ids).values_list('pk', flat=True)
        return list(object_ids)

    @staticmethod
    def get_by_id(pk) -> ChunkQuestionAttached:
        return ChunkQuestionAttachedMapper.get_by_id(pk)

    @staticmethod
    def batch_get_by_ids(ids) -> List[ChunkQuestionAttached]:
        return ChunkQuestionAttachedMapper.batch_get_by_ids(ids)
