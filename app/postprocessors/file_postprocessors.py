import json
from abc import abstractmethod
from typing import Dict

from app.workers.producers.producers import knowledge_index_task_kafka_producer, async_send_kafka_message
from init.settings import user_logger, DEFAULT_USER
from bella_rag.transformations.extractor.extractors import EXTRACTOR_SUMMARY
from bella_rag.utils.file_util import is_qa_knowledge


class FilePostProcessor:
    """文件后置处理器基类"""

    @abstractmethod
    def post_process(self, payload: Dict, **kwargs):
        """后置处理"""



class FileSummaryProcessor(FilePostProcessor):
    """文件摘要提取后置处理"""

    def post_process(self, payload: Dict, **kwargs):
        data = payload.get('data')
        file_id = data.get('id')
        file_name = data.get('filename')
        # 文件默认执行摘要提取
        from app.workers import knowledge_file_extractor_producer
        knowledge_file_summary_extract_msg = {
            "file_id": file_id,
            "request_id": file_id,
            "file_name": file_name,
            "extractors": [EXTRACTOR_SUMMARY],
            "ak_code": payload.get('ak_code'),
            "ak_sha": payload.get('ak_sha'),
            "ucid": DEFAULT_USER}
        async_send_kafka_message(knowledge_file_extractor_producer, json.dumps(knowledge_file_summary_extract_msg))
        user_logger.info(f'send file summary task : {file_id}')


class FileIndexingProcessor(FilePostProcessor):
    """文件索引构建处理"""

    def post_process(self, payload: Dict, **kwargs):
        if not payload.get('metadata'):
            return

        metadata = json.loads(payload.get('metadata'))
        if not isinstance(metadata, dict):
            user_logger.warn(f'vaild metadata is not dict : {payload}')
            return

        user_logger.info(f'receive event from file api metadata : {metadata}')

        data = payload.get('data')
        file_id = data.get('id')
        file_name = data.get('filename')
        city_list = metadata.get('city_list', ["全国"])
        callbacks = metadata.get('callbacks', [])

        indexing_metadata = {}
        if not is_qa_knowledge(file_name):
            # qa类型文件city list以文件内为准
            indexing_metadata["city_list"] = city_list

        indexing_data = {
            "metadata": indexing_metadata,
            "request_id": file_id,
            "file_id": file_id,
            "callbacks": callbacks,
            "file_name": file_name,
            "ak_code": payload.get('ak_code'),
            "ak_sha": payload.get('ak_sha'),
        }
        async_send_kafka_message(knowledge_index_task_kafka_producer, json.dumps(indexing_data))
        user_logger.info(f'send file indexing task : {file_id}')
