import json
from typing import List

from asgiref.sync import sync_to_async
from django.db import models


class QuestionAnswerIndexAttached(models.Model):
    id = models.AutoField(primary_key=True)  # 自增主键
    source_id = models.CharField(max_length=128, verbose_name='来源的id，文件为fileId')  # 来源的id
    group_id = models.CharField(max_length=128, null=False, blank=False, verbose_name='问题组的概念')
    question = models.TextField(verbose_name='问题')  # 问题文本
    answer = models.TextField(verbose_name='答案')  # 问题答案
    business_metadata = models.TextField(verbose_name='业务元数据字段，rag只提供读能力，业务方自由存储')  # 业务元数据字段
    del_status = models.IntegerField(default=0, verbose_name='删除状态')
    ctime = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')  # 创建时间
    mtime = models.DateTimeField(auto_now=True, verbose_name='更新时间')  # 更新时间

    class Meta:
        db_table = 'question_answer_index_attached'  # 指定数据库表名
        verbose_name = 'QA类型问题向量化索引信息'  # 模型的名称（在admin中显示）

    def to_dict(self):
        return {
            'id': self.id,
            'source_id': self.source_id,
            'group_id': self.group_id,
            'question': self.question,
            'business_metadata': self.business_metadata,
            'del_status': self.del_status,
            'answer': self.answer
        }

    def __str__(self):
        return json.dumps(self.__dict__, ensure_ascii=False, default=str)


class QuestionAnswerIndexAttachedMapper:

    @staticmethod
    def get_by_id_include_del(pk):
        return QuestionAnswerIndexAttached.objects.get(id=pk)

    @staticmethod
    def get_by_id(pk):
        return QuestionAnswerIndexAttached.objects.get(id=pk, del_status=0)

    @staticmethod
    def batch_get_by_ids_include_del(pk):
        return QuestionAnswerIndexAttached.objects.filter(id__in=pk)

    @staticmethod
    def batch_get_by_ids(pk):
        return QuestionAnswerIndexAttached.objects.filter(id__in=pk, del_status=0)

    @staticmethod
    def batch_get_by_ids_ignore_deleted(pk):
        return QuestionAnswerIndexAttached.objects.filter(id__in=pk)

    @staticmethod
    async def batch_get_by_ids_async_ignore_deleted(pk):
        return await sync_to_async(list)(QuestionAnswerIndexAttached.objects.filter(id__in=pk))

    @staticmethod
    def delete_by_source_id(source_id: str):
        return QuestionAnswerIndexAttached.objects.filter(source_id=source_id).update(del_status=1)

    @staticmethod
    def delete_by_group_id(group_id: str):
        return QuestionAnswerIndexAttached.objects.filter(group_id=group_id).update(del_status=1)

    @staticmethod
    def batch_save(question_answer_list_attached: List[QuestionAnswerIndexAttached]):
        return QuestionAnswerIndexAttached.objects.bulk_create(question_answer_list_attached, batch_size=100)

    @staticmethod
    def get_by_group_id(group_id: str):
        return QuestionAnswerIndexAttached.objects.filter(group_id=group_id, del_status=0)

    @staticmethod
    def save(record: QuestionAnswerIndexAttached):
        record.save()
        return record

    @staticmethod
    def batch_get_deleted_data(batch_size: int):
        return QuestionAnswerIndexAttached.objects.filter(del_status=1)[:batch_size]

    @staticmethod
    def delete_by_ids(ids: List[int]):
        QuestionAnswerIndexAttached.objects.filter(id__in=ids).delete()
