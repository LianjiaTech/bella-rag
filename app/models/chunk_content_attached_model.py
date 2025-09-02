import json
from typing import List

from asgiref.sync import sync_to_async
from django.db import models
from django.db.models.functions import Length


class ChunkContentAttached(models.Model):
    """
    因为数据安全问题腾讯向量库不允许保存content，所以增加此业务表辅助向量化保存结果
    """
    id = models.AutoField(primary_key=True)  # 显式定义 id 字段
    source_id = models.CharField(max_length=128, db_index=True, verbose_name='来源的id，文件为fileId')
    chunk_id = models.CharField(max_length=128, default='', db_index=True, verbose_name='chunk_id node_id')
    content_title = models.TextField(blank=True, null=True, verbose_name='标题')
    content_data = models.TextField(blank=True, null=True, verbose_name='内容')
    token = models.IntegerField(default=-911, verbose_name='节点及子节点token总量')
    chunk_pos = models.IntegerField(verbose_name='切片的位置')
    chunk_status = models.IntegerField(default=1, verbose_name='切片状态')
    order_num = models.CharField(max_length=128, default='', verbose_name='切片层级信息')
    context_id = models.CharField(max_length=128, default='', verbose_name='切片管理上下文id')
    create_time = models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, null=True, verbose_name='更新时间')

    class Meta:
        db_table = 'chunk_content_attached'
        verbose_name = '向量化索引信息保存'
        verbose_name_plural = '向量化索引信息保存'

    def __str__(self):
        return json.dumps(self.__dict__, ensure_ascii=False, default=str)

    def update_dict(self):
        return {
            'source_id': self.source_id,
            'chunk_id': self.chunk_id,
            'content_title': self.content_title,
            'content_data': self.content_data,
            'chunk_pos': self.chunk_pos,
            'token': self.token
        }

    def to_dict(self):
        return {
            'source_id': self.source_id,
            'chunk_id': self.chunk_id,
            'content_title': self.content_title,
            'content_data': self.content_data,
            'chunk_pos': self.chunk_pos,
            'chunk_status': self.chunk_status,
            'order_num': self.order_num,
            'context_id': self.context_id,
            'token': self.token
        }


class ChunkContentAttachedMapper:

    @staticmethod
    def get_by_id(pk: int):
        return ChunkContentAttached.objects.get(id=pk)

    @staticmethod
    def get_by_chunk_id(chunk_id: str):
        return ChunkContentAttached.objects.get(chunk_id=chunk_id)

    @staticmethod
    def source_has_exist(source_id: str) -> bool:
        return ChunkContentAttached.objects.exists(source_id=source_id)

    @staticmethod
    def save(chunk_content_attached: ChunkContentAttached):
        ChunkContentAttached.objects.update_or_create(defaults=chunk_content_attached.update_dict(),
                                                      chunk_id=chunk_content_attached.chunk_id)

    @staticmethod
    def batch_save(chunk_content_attached_list: List[ChunkContentAttached], connection=None):
        if not chunk_content_attached_list:
            return

        table_name = ChunkContentAttached._meta.db_table
        fields = ['chunk_id', 'source_id', 'content_title', 'content_data', 'chunk_pos', 'chunk_status',
                  'token', 'order_num']  # 替换为实际字段名
        update_fields = ['source_id', 'content_title', 'content_data', 'chunk_pos', 'chunk_status',
                         'token', 'order_num']  # 替换为实际需要更新的字段

        values = []
        for obj in chunk_content_attached_list:
            values.append((
                obj.chunk_id, obj.source_id, obj.content_title.encode('utf-8', 'replace').decode('utf-8'),
                obj.content_data.encode('utf-8', 'replace').decode('utf-8'), obj.chunk_pos, obj.chunk_status,
                obj.token, obj.order_num
            ))

        fields_str = ', '.join([connection.ops.quote_name(field) for field in fields])
        update_str = ', '.join(
            [f"{connection.ops.quote_name(field)}=VALUES({connection.ops.quote_name(field)})"
             for field in update_fields])

        sql = f"""
                        INSERT INTO {connection.ops.quote_name(table_name)} ({fields_str})
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE {update_str};
                        """

        # 使用 connections['default'] 来确保每次请求时新建数据库连接
        with connection.cursor() as cursor:
            cursor.executemany(sql, values)

    @staticmethod
    def logic_delete_by_id(pk: int):
        chunk = ChunkContentAttached.objects.get(id=pk)
        chunk.chunk_status = 0
        chunk.save()

    @staticmethod
    def logic_delete_by_chunk_id(chunk_Id: int):
        chunk = ChunkContentAttached.objects.get(chunk_id=chunk_Id)
        chunk.chunk_status = 0
        chunk.save()

    @staticmethod
    def batch_get_by_chunk_ids(chunk_ids: List[str]):
        return ChunkContentAttached.objects.filter(chunk_id__in=chunk_ids)

    @staticmethod
    async def batch_get_by_chunk_ids_async(chunk_ids: List[str]):
        return await sync_to_async(list)(ChunkContentAttached.objects.filter(chunk_id__in=chunk_ids))

    @staticmethod
    def logic_delete_by_source_id(source_id: str):
        chunks = ChunkContentAttached.objects.filter(source_id=source_id)
        if chunks.exists():
            chunks.update(chunk_status=0)

    @staticmethod
    def delete_by_chunk_id(chunk_id: int):
        return ChunkContentAttached.objects.filter(chunk_id=chunk_id).delete()

    @staticmethod
    def delete_by_chunk_ids(chunk_ids: List[str]):
        return ChunkContentAttached.objects.filter(chunk_id__in=chunk_ids).delete()

    @staticmethod
    def delete_by_source_id(source_id: str):
        return ChunkContentAttached.objects.filter(source_id=source_id).delete()

    @staticmethod
    def chunk_pos_increment(source_id: str, index: int):
        ChunkContentAttached.objects.filter(source_id=source_id, chunk_pos__gte=index) \
            .update(chunk_pos=models.F('chunk_pos') + 1)

    @staticmethod
    def chunk_pos_decrement(source_id: str, index: int):
        ChunkContentAttached.objects.filter(source_id=source_id, chunk_pos__gte=index) \
            .update(chunk_pos=models.F('chunk_pos') - 1)

    @staticmethod
    def find_max_id_chunk(source_id: str):
        # ORDER BY LENGTH(chunk_id) DESC, chunk_id DESC;
        return ChunkContentAttached.objects.filter(source_id=source_id).annotate(chunk_id_length=Length('chunk_id')) \
            .order_by('-chunk_id_length', '-chunk_id').first()

    @staticmethod
    def chunk_token_update(source_id: str, order_nums: List[str], token_diff: int):
        ChunkContentAttached.objects.filter(source_id=source_id, order_num__in=order_nums, token__gt=0) \
            .update(token=models.F('token') + token_diff)

    @staticmethod
    def batch_get_by_source_id(source_id: str, limit: int, offset: int):
        chunks = (ChunkContentAttached.objects
                  .filter(source_id=source_id)
                  .order_by('chunk_pos')[offset:offset + limit])
        return chunks

    @staticmethod
    def search_structure_nodes(source_id: str, limit: int, offset: int):
        chunks = (ChunkContentAttached.objects
                  .filter(source_id=source_id)
                  .exclude(order_num__isnull=True)
                  .exclude(order_num='')
                  .order_by('chunk_pos')[offset:offset + limit])
        return chunks

    @staticmethod
    def update_chunks_context_id(chunk_ids: List[str], context_id: str):
        ChunkContentAttached.objects.filter(chunk_id__in=chunk_ids) \
            .update(context_id=context_id)

    @staticmethod
    def batch_get_by_context_id(context_id: str, limit: int, offset: int):
        chunks = (ChunkContentAttached.objects
                  .filter(context_id=context_id)
                  .order_by('chunk_pos')[offset:offset + limit])
        return chunks

    @staticmethod
    def get_distinct_context_ids_by_source_id(source_id: str):
        chunk_ids = (ChunkContentAttached.objects
                       .filter(source_id=source_id)
                       .filter(context_id='')
                       .filter(order_num='')
                     .values_list('chunk_id', flat=True)
                       .distinct())
        return list(chunk_ids)

    @staticmethod
    def update_source_context_id(source_id: str, context_id: str):
        ChunkContentAttached.objects.filter(source_id=source_id) \
            .update(context_id=context_id)


