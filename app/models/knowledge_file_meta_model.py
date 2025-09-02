import json
from typing import List

from django.db import models


class KnowledgeFileMeta(models.Model):
    id = models.BigAutoField(primary_key=True, verbose_name='主键')
    file_id = models.CharField(max_length=64, default='', verbose_name='来源')
    summary_question = models.TextField(verbose_name='总结')
    tag = models.TextField(verbose_name='业务标签')

    class Meta:
        db_table = 'knowledge_file_meta'
        verbose_name = '知识文件维度的元数据'

    def __str__(self):
        return json.dumps(self.__dict__, ensure_ascii=False, default=str)

    def update_dict(self):
        result = {}
        if self.summary_question:
            result.update({'summary_question': self.summary_question})
        if self.tag:
            result.update({'tag': self.tag})
        return result


class KnowledgeFileMetaMapper:

    @staticmethod
    def get_by_file_id(file_id: str):
        return KnowledgeFileMeta.objects.get(file_id=file_id)

    @staticmethod
    def batch_get_by_file_ids(file_ids: List[str]):
        return KnowledgeFileMeta.objects.filter(file_id__in=file_ids)

    @staticmethod
    def save(knowledge_file_meta: KnowledgeFileMeta):
        KnowledgeFileMeta.objects.update_or_create(defaults=knowledge_file_meta.update_dict(),
                                                   file_id=knowledge_file_meta.file_id)

    @staticmethod
    def delete_by_file_id(file_id: str):
        KnowledgeFileMeta.objects.filter(file_id=file_id).delete()
