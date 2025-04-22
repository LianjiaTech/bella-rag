import json
from typing import List

from django.db import models, transaction
from django.db.models import F
from django.utils import timezone


class FileAccessRecord(models.Model):
    id = models.BigAutoField(primary_key=True, verbose_name='主键')
    file_id = models.CharField(max_length=128, default='', verbose_name='文件id')
    last_accessed = models.DateTimeField(auto_now=True, verbose_name='最新一次访问时间')
    access_count = models.IntegerField(default=0, verbose_name='访问次数')

    class Meta:
        db_table = 'file_access_record'
        verbose_name = 'rag文件访问记录'

    def __str__(self):
        return json.dumps(self.__dict__, ensure_ascii=False, default=str)

    def update_dict(self):
        result = {}
        if self.last_accessed:
            result.update({'last_accessed': self.last_accessed})
        if self.access_count:
            result.update({'taccess_countag': self.access_count})
        return result


class FileAccessRecordMapper:

    @staticmethod
    def update_or_create_file_access_records(file_ids):
        if not file_ids:
            return
        current_time = timezone.now()

        with transaction.atomic():
            # 获取所有已存在的记录
            existing_records = FileAccessRecord.objects.filter(file_id__in=file_ids)

            # 创建一个字典用于快速查找
            existing_records_dict = {record.file_id: record for record in existing_records}

            # 准备更新和创建的列表
            records_to_update = []
            new_records = []

            for file_id in file_ids:
                if file_id in existing_records_dict:
                    # 更新现有记录
                    record = existing_records_dict[file_id]
                    record.last_accessed = current_time
                    record.access_count = F('access_count') + 1
                    records_to_update.append(record)
                else:
                    # 创建新记录
                    new_records.append(FileAccessRecord(
                        file_id=file_id,
                        last_accessed=current_time,
                        access_count=1
                    ))

            # 批量更新
            if records_to_update:
                FileAccessRecord.objects.bulk_update(records_to_update, ['last_accessed', 'access_count'])

            # 批量创建
            if new_records:
                FileAccessRecord.objects.bulk_create(new_records)
