import json
from typing import List, Set, Union

from django.db import models


class ChunkQuestionAttached(models.Model):
    id = models.AutoField(primary_key=True)  # 自增主键
    source_id = models.CharField(max_length=128, verbose_name='来源的id，文件为fileId')  # 来源的id
    chunk_id = models.CharField(max_length=128, default='', verbose_name='chunk_id node_id')  # chunk_id
    question = models.TextField(verbose_name='问题')  # 问题文本
    question_type = models.CharField(max_length=32, default='', verbose_name='问题类型')
    ctime = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')  # 创建时间
    mtime = models.DateTimeField(auto_now=True, verbose_name='更新时间')  # 更新时间

    class Meta:
        db_table = 'chunk_question_attached'  # 指定数据库表名
        verbose_name = 'QA类型问题向量化索引信息'  # 模型的名称（在admin中显示）

    def __str__(self):
        return json.dumps(self.__dict__, ensure_ascii=False, default=str)


class ChunkQuestionAttachedMapper:

    @staticmethod
    def get_by_id(pk):
        return ChunkQuestionAttached.objects.get(id=pk)

    @staticmethod
    def batch_get_by_ids(pk):
        return ChunkQuestionAttached.objects.filter(id__in=pk)

    @staticmethod
    def get_by_chunk_id(chunk_id: str):
        return ChunkQuestionAttached.objects.get(chunk_id=chunk_id)

    @staticmethod
    def delete_by_chunk_id(chunk_id: str):
        return ChunkQuestionAttached.objects.filter(chunk_id=chunk_id).delete()

    @staticmethod
    def delete_by_chunk_ids(chunk_ids: Union[List[str], Set[str]]):
        return ChunkQuestionAttached.objects.filter(chunk_id__in=chunk_ids).delete()

    @staticmethod
    def batch_save(chunk_question_attached: List[ChunkQuestionAttached]):
        return ChunkQuestionAttached.objects.bulk_create(chunk_question_attached, batch_size=100)
