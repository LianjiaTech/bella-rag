from concurrent.futures import ThreadPoolExecutor
from typing import List

from app.services.file_access_record_service import FileAccessRecordService

# 全局线程池
logging_executor = ThreadPoolExecutor(max_workers=5)

def async_log_file_ids(file_ids: List[str]):
    """
    文件检索记录，后续统计长期未参与检索文件需要
    """
    if file_ids:
        logging_executor.submit(
            FileAccessRecordService.update_or_create_file_access_records,
            file_ids.copy()
        )
