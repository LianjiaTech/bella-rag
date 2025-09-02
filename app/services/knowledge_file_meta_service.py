from typing import List

from app.models.knowledge_file_meta_model import KnowledgeFileMetaMapper, KnowledgeFileMeta


class KnowledgeMetaService:

    @staticmethod
    def save(knowledge_file_meta: KnowledgeFileMeta):
        KnowledgeFileMetaMapper.save(knowledge_file_meta=knowledge_file_meta)

    @staticmethod
    def get_by_file_id(file_id: str) -> KnowledgeFileMeta:
        return KnowledgeFileMetaMapper.get_by_file_id(file_id=file_id)

    @staticmethod
    def delete_by_file_id(file_id: str) -> KnowledgeFileMeta:
        return KnowledgeFileMetaMapper.delete_by_file_id(file_id=file_id)

    @staticmethod
    def batch_get_by_file_ids(file_ids: List[str]) -> List[KnowledgeFileMeta]:
        return KnowledgeFileMetaMapper.batch_get_by_file_ids(file_ids=file_ids)
