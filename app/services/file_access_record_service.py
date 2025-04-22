from app.models.file_access_record_model import FileAccessRecordMapper
from init.settings import user_logger


class FileAccessRecordService:

    @staticmethod
    def update_or_create_file_access_records(file_ids):
        try:
            user_logger.debug(f'update_or_create_file_access_records {file_ids}')
            FileAccessRecordMapper.update_or_create_file_access_records(file_ids)
        except Exception as e:
            user_logger.error(f"update_or_create_file_access_records failed: {str(e)}")
