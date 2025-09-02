from typing import List

import redis
from django.db import transaction

from app.services import EXTRA_DOC_TYPE_KEY
from app.services.chunk_content_attached_service import ChunkContentAttachedService
from app.strategy import es_store
from app.utils.convert import _extra_data_from_dict_to_list, convert_chunk_content_attached
from common.tool.redis_tool import redis_pool
from common.tool.vector_db_tool import vector_store
from init.settings import user_logger
from bella_rag.meta.meta_data import NodeTypeEnum
from bella_rag.schema.nodes import TextNode

redis_key_prefix = "file_context_summary_success_"
redis_client = redis.Redis(connection_pool=redis_pool)


@transaction.atomic
def save_context_chunk(source_id: str, source_name: str, context_text: str, context_id: str,
                       sub_ids: List[str], extra: dict, embedding: List[float], token: int = -911):
    # todo 耗时可以优化
    user_logger.info(f'start save context chunk. source_id: {source_id}, source_name: {source_name}, '
                     f'context_text: {context_text}, context_id: {context_id}, extra: {extra}, token:{token}')
    extra['context_id'] = context_id
    # extra添加节点补充类型字段标识区分context节点
    extra[EXTRA_DOC_TYPE_KEY] = 'contextual'
    meta = {"source_id": source_id, "source_name": source_name, "node_type": NodeTypeEnum.TEXT.node_type_code,
            "context_id": context_id, "extra": _extra_data_from_dict_to_list(extra)}
    id_pos = ChunkContentAttachedService.find_max_id_pos(source_id) + 1
    node_id = source_id + '-' + str(id_pos)
    node = TextNode(id_=node_id, text=context_text, metadata=meta)
    node.embedding = embedding
    node.token = token
    ChunkContentAttachedService.chunk_pos_increment(source_id, 0)
    ChunkContentAttachedService.save(convert_chunk_content_attached(0, node))
    user_logger.info("save_context_chunk success chunk_id = %s [step=插入数据库]", node_id)

    # 更新mysql数据库chunk表context_id
    ChunkContentAttachedService.update_chunks_context_id(sub_ids, context_id)
    user_logger.info("save_context_chunk success chunk_id = %s [step=更新chunk上下文id]", node_id)
    vector_store.add([node])
    user_logger.info("save_context_chunk success chunk_id = %s [step=插入向量库]", node_id)
    es_store.add([node])
    user_logger.info("save_context_chunk success chunk_id = %s [step=插入es索引]", node_id)


@transaction.atomic
def clear_context_nodes(source_id: str):
    """
    清理文件的context节点
    """
    user_logger.info(f'start clear context chunks. source_id: {source_id}')
    structure_node_sample = ChunkContentAttachedService.find_structure_node(source_id, 1, 0)
    if not structure_node_sample:
        user_logger.info(f'file: {source_id} is not structured, skip context clear')
        return

    # 查询所有context节点id
    context_chunk_ids = ChunkContentAttachedService.get_distinct_context_ids_by_source_id(source_id)
    if not context_chunk_ids:
        return

    # 删除向量库数据
    vector_store.delete_documents(context_chunk_ids)
    # 删除es数据
    es_store.delete_nodes(node_ids=context_chunk_ids)

    # 清空数据库数据
    ChunkContentAttachedService.delete_by_chunk_ids(context_chunk_ids)
    # 清空节点关联context id
    ChunkContentAttachedService.update_source_context_id(source_id, '')
    user_logger.info(f'finish clear context chunks. source_id: {source_id}')
    # 删除redis记录
    redis_client.delete(redis_key_prefix + source_id)
