import redis
from redis_lock import Lock

from app.services import es_index_structure, chunk_vector_index_structure, question_vector_index_structure, file_service
from app.services.chunk_content_attached_service import ChunkContentAttachedService
from app.services.knowledge_file_meta_service import KnowledgeMetaService
from app.services.question_answer_attached_service import QuestionAnswerIndexAttachedService
from app.strategy import es_store
from common.tool.redis_tool import redis_pool
from common.tool.vector_db_tool import vector_store, questions_vector_store
from init.settings import user_logger
from bella_rag.utils.schema_util import node_cache

logger = user_logger


def knowledge_file_delete_callback(payload: dict) -> bool:
    file_id = payload.get('file_id')

    lock = Lock(redis_client=redis.Redis(connection_pool=redis_pool),
                name=f"knowledge_file_index_done_task_lock_{file_id}",
                auto_renewal=True,
                expire=180)
    try:
        lock.acquire()
        user_logger.info(f'start delete file : {file_id}')
        # 删除mysql数据
        ChunkContentAttachedService.delete_by_source_id(source_id=file_id)
        QuestionAnswerIndexAttachedService.delete_by_source_id(source_id=file_id)
        KnowledgeMetaService.delete_by_file_id(file_id=file_id)

        # 删除向量库数据
        logger.info("delete_file success file_id = %s [step=更新数据库]", file_id)
        vector_store.delete(ref_doc_id=file_id, delete_key=chunk_vector_index_structure.doc_id_key)
        logger.info("delete_file success file_id = %s [step=更新Chunk向量库]", file_id)

        questions_vector_store.delete(ref_doc_id=file_id, delete_key=question_vector_index_structure.doc_id_key)
        logger.info("delete_file success file_id = %s [step=更新QA向量库]", file_id)

        es_store.delete(ref_doc_id=file_id, delete_key=es_index_structure.doc_id_key)
        logger.info("delete_file success file_id = %s [step=更新es索引]", file_id)
        # 删除缓存数据
        node_cache.remove(file_id=file_id)
        logger.info("delete_file success file_id = %s [step=清理缓存]", file_id)
        file_service.remove_deleted_files_record([file_id])

    finally:
        if lock.locked():
            lock.release()
    return True
