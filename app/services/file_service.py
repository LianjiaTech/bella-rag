import json
from io import IOBase
from threading import Thread
from typing import List, Optional

import redis
from llama_index.core import StorageContext, Document
from llama_index.core.graph_stores import SimpleGraphStore
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore
from llama_index.core.vector_stores import VectorStoreQuery
from llama_index.core.vector_stores.simple import DEFAULT_VECTOR_STORE

from app.common.contexts import UserContext, TraceContext
from app.handler.custom_error_handler import custom_exception_handler
from app.services import chunk_vector_index_structure, embed_model, question_vector_index_structure
from app.services.context_service import vector_store
from app.services.index_extend.db_transformation import ChunkContentAttachedIndexExtend, \
    QuestionAnswerAttachedIndexExtend
from app.services.knowledge_file_meta_service import KnowledgeMetaService
from app.services.qa_service import questions_vector_store
from app.utils.convert import _extra_data_from_dict_to_list, logger
from app.utils.convert import trans_metadata_to_extra
from app.workers.producers.producers import knowledge_file_delete_producer, async_send_kafka_message
from common.helper.exception import UnsupportedTypeError, FileCheckException
from common.tool.redis_tool import redis_pool
from common.tool.vector_db_tool import summary_question_vector_store
from init.settings import user_logger
from bella_rag.callbacks.manager import init_callbacks
from bella_rag.meta.meta_data import NodeTypeEnum
from bella_rag.transformations.domtree import domtree_parser
from bella_rag.transformations.domtree.domtree_transformation import DomTreeParser
from bella_rag.transformations.extractor.extractors import EXTRACTOR_CONTEXT
from bella_rag.transformations.factory import TransformationFactory
from bella_rag.utils.file_api_tool import file_api_client
from bella_rag.utils.file_util import get_file_type, is_qa_knowledge
from bella_rag.utils.trace_log_util import trace
from bella_rag.vector_stores.factory import has_index, get_index
from bella_rag.vector_stores.types import MetadataFilter
from bella_rag.vector_stores.types import MetadataFilters, FilterOperator
from bella_rag.vector_stores.vector_store import ManyVectorStoreIndex

redis_client = redis.Redis(connection_pool=redis_pool)
deleted_files_key = "rag:deleted_file_ids"


def run_index_file(file_id: str, file_name: str, documents: list, transforms: list,
                   metadata: Optional[dict], callbacks: List[str], user: str):
    """索引建立"""
    UserContext.user_id = user
    init_callbacks(callbacks)

    user_logger.info(f'start indexing file : {file_id}, name : {file_name}, metadata:{metadata}')

    # 向量存储配置
    vector_stores = {}
    if has_index("es_index"):
        es_index = get_index("es_index")
        vector_stores['elasticsearch'] = es_index.vector_store

    # 区分 QA 与知识文件
    if is_qa_knowledge(file_name):
        vector_stores[DEFAULT_VECTOR_STORE] = questions_vector_store
        transforms.append(QuestionAnswerAttachedIndexExtend())
    else:
        vector_stores[DEFAULT_VECTOR_STORE] = vector_store
        transforms.append(ChunkContentAttachedIndexExtend())

    storage_context = StorageContext(
        docstore=SimpleDocumentStore(),
        index_store=SimpleIndexStore(),
        vector_stores=vector_stores,
        graph_store=SimpleGraphStore(),
    )

    ManyVectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        transformations=transforms,
        embed_model=embed_model,
        metadata=get_document_metadata(file_id=file_id, file_name=file_name, metadata=metadata),
    )

    # 发送文件处理完成的消息
    from app.workers import knowledge_file_extractor_producer
    knowledge_file_index_done_msg = {
        "file_id": file_id,
        "request_id": TraceContext.trace_id,
        "file_name": file_name,
        "extractors": [EXTRACTOR_CONTEXT],
        "ucid": user,
        "ak_code": UserContext.usage_ak_code,
        "ak_sha": UserContext.usage_ak_sha,
    }
    async_send_kafka_message(knowledge_file_extractor_producer, json.dumps(knowledge_file_index_done_msg))
    user_logger.info(f'finish indexing file : {file_id}')


'''
注意：这个函数不可重入，index中的node id和位置有关系，一旦文件或parser算法发生改变，都需要重建index & index-extend
'''


@custom_exception_handler()
@trace(step='multi_index_construction', progress="file_indexing")
def file_indexing(file_id: str, file_name: str, metadata: Optional[dict] = None,
                  callbacks: List[str] = None, user: str = None, custom_parsers: Optional[dict] = None):
    """
    结合fileapi，支持效果更优的domtree解析
    """
    file_type = get_file_type(file_name)

    # 文件大小校验
    file = file_api_client.get_file_info(file_id)
    if file and int(file.get('bytes')) > 30000000:
        raise FileCheckException(f"文件大小超过30M：{file.get('bytes')}")

    transforms = []
    if DomTreeParser.supports_file_type(file_type):
        transforms.append(domtree_parser)
        documents = [Document(doc_id=file_id)]
    else:
        reader = TransformationFactory.get_reader(file_type)
        if not reader:
            raise UnsupportedTypeError(f'不支持的文件类型：{file_type}')
        transforms.append(TransformationFactory.get_parser(file_type, custom_parsers))
        documents = reader.load_file(file_id=file_id)

    run_index_file(file_id, file_name, documents, transforms, metadata, callbacks, user)


@trace(step='multi_index_construction', progress="file_stream_indexing")
def file_stream_indexing(file_id: str, file_name: str, file_stream: IOBase, metadata: Optional[dict] = None,
                         callbacks: List[str] = None, user: str = None, custom_parsers: Optional[dict] = None):
    """
    通过文件流解析，适用于简单的解析策略
    """
    file_type = get_file_type(file_name)

    reader = TransformationFactory.get_reader(file_type)
    if not reader:
        raise UnsupportedTypeError(f'不支持的文件类型：{file_type}')

    transforms = [TransformationFactory.get_parser(file_type, custom_parsers)]
    documents = reader.load_data(stream=file_stream)

    run_index_file(file_id, file_name, documents, transforms, metadata, callbacks, user)


def async_file_indexing(file_id: str, file_name: str, metadata: dict, callbacks: List[str] = None, user: str = None):
    if not file_name:
        return
    thread = Thread(
        target=lambda: file_indexing(file_id=file_id, file_name=file_name, metadata=metadata,
                                     callbacks=callbacks, user=user))
    thread.start()


def get_document_metadata(file_id: str, file_name: str, metadata: dict):
    return {"source_id": file_id, "source_name": file_name, "extra": trans_metadata_to_extra(metadata)}


def file_update(source_id: str, extra: dict):
    extra_list = _extra_data_from_dict_to_list(extra)
    node_types = [NodeTypeEnum.TEXT.node_type_code]
    update_extra(source_id, node_types, extra_list)
    logger.info("batch_update_chunk success source_id = %s [step=更新向量库]", source_id)


def update_extra(
        source_id: str,
        node_types: List[str],
        extra_list: List[str]
) -> List[str]:
    document = Document(extra=extra_list)

    # 使用统一的MetadataFilters接口
    metadata_filters = MetadataFilters(
        filters=[
            MetadataFilter(key="source_id", value=[source_id], operator=FilterOperator.IN),
            MetadataFilter(key="node_type", value=node_types, operator=FilterOperator.IN)
        ]
    )

    vector_store.update_vector(metadata_filters, document)
    return [source_id]


def get_file_summary(file_ids: List[str], query: str, top_k: int):
    embeddings = embed_model.get_text_embedding(text=query)
    filters = [MetadataFilter(key="source_id", value=file_ids, operator=FilterOperator.IN)]
    metadata_filters = MetadataFilters(filters=filters)
    vector_query = VectorStoreQuery(query_str=query, query_embedding=embeddings, similarity_top_k=top_k,
                                    filters=metadata_filters)
    query_res = summary_question_vector_store.query(query=vector_query, index=chunk_vector_index_structure)
    file_metas = KnowledgeMetaService.batch_get_by_file_ids(file_ids=query_res.ids)
    file_meta_map = {}
    for file_meta in file_metas:
        file_meta_map[file_meta.file_id] = file_meta.summary_question

    res = []
    for i, node in enumerate(query_res.nodes):
        res.append({'file_id': node.node_id,
                    'summary': file_meta_map.get(node.node_id),
                    'score': query_res.similarities[i]})

    return res


def get_file_summaries(file_ids: List[str]):
    if not file_ids:
        return []
    file_metas = KnowledgeMetaService.batch_get_by_file_ids(file_ids=file_ids)
    res = []
    for file_meta in file_metas:
        res.append({'file_id': file_meta.file_id, 'summary': file_meta.summary_question})

    return res


def record_deleted_file(file_id: str):
    if not file_id:
        return
    redis_client.sadd(deleted_files_key, file_id)


def remove_deleted_files_record(file_ids: List[str]):
    if not file_ids:
        return
    for file_id in file_ids:
        redis_client.srem(deleted_files_key, file_id)


@trace("filter_deleted_files")
def filter_deleted_files(file_ids: List[str]) -> List[str]:
    if not file_ids:
        return []
    with redis_client.pipeline() as pipe:
        # 将所有sismember命令添加到pipeline中
        for file_id in file_ids:
            pipe.sismember(deleted_files_key, file_id)
        results = pipe.execute()
    # 根据结果过滤出不存在于deleted_files_set中的文件ID
    return [file_id for file_id, exists in zip(file_ids, results) if not exists]


def file_delete_submit_task(file_id: str) -> bool:
    # 发送文件处理完成的消息
    knowledge_file_delete_msg = {
        "file_id": file_id,
    }
    # 记录文件的删除状态
    record_deleted_file(file_id)
    return async_send_kafka_message(knowledge_file_delete_producer, json.dumps(knowledge_file_delete_msg))


def rename_file(file_id: str, file_name: str):
    user_logger.info(f'start rename file : {file_id} to {file_name}')

    try:
        # 更新chunk向量存储中的文件名
        vector_store.update_field_by_filter(
            filter_key="source_id",
            filter_value=file_id,
            field_name=chunk_vector_index_structure.doc_name_key,
            field_value=file_name
        )
        questions_vector_store.update_field_by_filter(
            filter_key="source_id",
            filter_value=file_id,
            field_name=question_vector_index_structure.doc_name_key,
            field_value=file_name
        )
        user_logger.info(f'rename file completed: {file_id} to {file_name}')
    except Exception as e:
        user_logger.error(f'Failed to rename file: {file_id}, error: {e}')
        raise
