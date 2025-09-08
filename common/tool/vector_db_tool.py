import os
from typing import List, Optional

from app.services.index_extend.db_transformation import ChunkContentAttachedIndexExtend, \
    QuestionAnswerAttachedIndexExtend
from bella_rag.schema.nodes import BaseNode
from app.services import embed_model, chunk_vector_index_structure, question_vector_index_structure
from bella_rag.vector_stores import qdrant_manager, tencent_manager
from bella_rag.vector_stores.types import MetadataFilter, FilterOperator, MetadataFilters

chunk_index_extend = ChunkContentAttachedIndexExtend()
question_answer_extend = QuestionAnswerAttachedIndexExtend()

vector_store = None
questions_vector_store = None
# 腾讯向量库读实时性高的场景，需要连接主库
master_vector_store = None
master_questions_vector_store = None
summary_question_vector_store = None


def get_vector_db_type() -> str:
    """获取向量数据库类型"""
    # 优先级：环境变量 > 配置文件 > 默认值(qdrant)
    return (
            os.getenv('VECTOR_DB_TYPE') or
            getattr(__import__('init.settings', fromlist=['VECTOR_DB_TYPE']), 'VECTOR_DB_TYPE', 'qdrant')
    ).lower()


def init_vector_stores():
    """初始化向量存储"""
    global vector_store, master_vector_store, questions_vector_store, master_questions_vector_store, summary_question_vector_store
    
    if get_vector_db_type() == 'qdrant':
        qdrant_manager.init_stores()
        vector_store = qdrant_manager.get_chunk_store()
        master_vector_store = vector_store  # Qdrant不需要区分master
        questions_vector_store = qdrant_manager.get_qa_store()
        master_questions_vector_store = questions_vector_store
        summary_question_vector_store = qdrant_manager.get_summary_store()
    else:
        tencent_manager.init_stores()
        vector_store = tencent_manager.get_chunk_store(master=False)
        master_vector_store = tencent_manager.get_chunk_store(master=True)
        questions_vector_store = tencent_manager.get_qa_store(master=False)
        master_questions_vector_store = tencent_manager.get_qa_store(master=True)
        summary_question_vector_store = tencent_manager.get_summary_store(master=False)


def query_all_by_source(source_id: str, read_strong_consistency: bool = False) -> List[BaseNode]:
    start = 0
    limit = 5000
    res = []
    while True:
        query_res = batch_query_by_source(source_id, limit, start, read_strong_consistency)
        if not query_res:
            break
        res.extend(query_res)
        start += limit
    return res


def batch_query_by_source(source_id: str, limit: int, offset: int, read_strong_consistency: bool = False,
                          ) -> List[BaseNode]:
    if not source_id:
        return []
    if not vector_store and not master_vector_store:
        return []

    store = master_vector_store if read_strong_consistency and master_vector_store else vector_store

    # 构建业务层的查询条件
    filters = [
        MetadataFilter(key="source_id", value=source_id, operator=FilterOperator.EQ)
    ]

    metadata_filters = MetadataFilters(filters=filters)
    return store.query_by_filter(
        limit=limit,
        offset=offset,
        filter_condition=metadata_filters,
        index_extend=chunk_index_extend,
        index=chunk_vector_index_structure,
    )


def batch_question_by_filter(source_id: str, limit: int, offset: int, group_ids: Optional[List[str]] = None,
                             ids: Optional[List[str]] = None,
                             read_strong_consistency: bool = False) -> List[BaseNode]:
    if not questions_vector_store and not master_questions_vector_store:
        return []
    store = master_questions_vector_store if read_strong_consistency and master_questions_vector_store else questions_vector_store

    filters = []
    if source_id:
        filters.append(MetadataFilter(key="source_id", value=source_id, operator=FilterOperator.EQ))

    if group_ids:
        filters.append(
            MetadataFilter(key="group_id", value=group_ids, operator=FilterOperator.IN)
        )

    metadata_filters = MetadataFilters(filters=filters)

    # 调用底层向量数据库的查询能力
    return store.query_by_filter(
        limit=limit,
        offset=offset,
        document_ids=ids,
        filter_condition=metadata_filters,
        index=question_vector_index_structure,
        index_extend=question_answer_extend,
    )


# 初始化向量存储
init_vector_stores()
