from typing import List

from django.db import transaction

from app.models.question_answer_attached_model import QuestionAnswerIndexAttached, QuestionAnswerIndexAttachedMapper


class QuestionAnswerIndexAttachedService:
    @staticmethod
    @transaction.atomic
    def coverage_data(question_answer_attached_list: List[QuestionAnswerIndexAttached]):
        """覆盖数据：先删除后插入，在事务里，用户只能感知最后结果"""
        if not question_answer_attached_list:
            return []
        source_id = question_answer_attached_list[0].source_id
        QuestionAnswerIndexAttachedMapper.delete_by_source_id(source_id=source_id)
        QuestionAnswerIndexAttachedMapper.batch_save(question_answer_attached_list)
        object_ids = QuestionAnswerIndexAttached.objects.filter(source_id=source_id).values_list('pk', flat=True)
        return list(object_ids)


    @staticmethod
    def get_by_id_include_del(pk):
        return QuestionAnswerIndexAttachedMapper.get_by_id_include_del(pk)

    @staticmethod
    def get_by_id(pk) -> QuestionAnswerIndexAttached:
        return QuestionAnswerIndexAttachedMapper.get_by_id(pk)

    @staticmethod
    def batch_get_by_ids_include_del(ids) -> List[QuestionAnswerIndexAttached]:
        return QuestionAnswerIndexAttachedMapper.batch_get_by_ids_include_del(ids)

    @staticmethod
    def batch_get_by_ids(ids) -> List[QuestionAnswerIndexAttached]:
        return QuestionAnswerIndexAttachedMapper.batch_get_by_ids(ids)

    @staticmethod
    def batch_get_by_ids_ignore_deleted(ids) -> List[QuestionAnswerIndexAttached]:
        return QuestionAnswerIndexAttachedMapper.batch_get_by_ids_ignore_deleted(ids)

    @staticmethod
    async def async_batch_get_by_ids_ignore_deleted(ids):
        yield await QuestionAnswerIndexAttachedMapper.batch_get_by_ids_async_ignore_deleted(ids)

    @staticmethod
    def delete_by_group_id(group_id: str):
        return QuestionAnswerIndexAttachedMapper.delete_by_group_id(group_id=group_id)

    @staticmethod
    def get_by_group_id(group_id: str) -> List[QuestionAnswerIndexAttached]:
        return QuestionAnswerIndexAttachedMapper.get_by_group_id(group_id=group_id)

    @staticmethod
    def save(item: QuestionAnswerIndexAttached):
        QuestionAnswerIndexAttachedMapper.save(item)

    @staticmethod
    def delete_by_source_id(source_id: str):
        return QuestionAnswerIndexAttachedMapper.delete_by_source_id(source_id=source_id)

    @staticmethod
    def delete_batches(batch_size: int):
        while True:
            # 获取一批要删除的数据
            to_delete = QuestionAnswerIndexAttachedMapper.batch_get_deleted_data(batch_size)

            if not to_delete:
                break  # 如果没有数据了，退出循环

            with transaction.atomic():
                # 获取要删除对象的主键列表
                ids_to_delete = list(to_delete.values_list('id', flat=True))
                # 使用主键列表删除对象
                QuestionAnswerIndexAttachedMapper.delete_by_ids(ids_to_delete)
