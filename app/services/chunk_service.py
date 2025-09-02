from typing import List

from django.db import transaction
from llama_index.core.indices.utils import embed_nodes

from app.services import chunk_vector_index_structure, embed_model
from app.services.chunk_content_attached_service import ChunkContentAttachedService
from app.services.index_extend.db_transformation import set_node_content
from app.strategy import es_store
from app.utils.convert import extract_metadata_from_extra, convert_chunk_content_attached, _extra_data_from_dict_to_list
from common.helper.exception import ChunkOperateError
from common.tool.vector_db_tool import vector_store, batch_query_by_source
from init.settings import user_logger
from bella_rag.meta.meta_data import NodeTypeEnum
from bella_rag.schema.nodes import TextNode, ImageNode, QaNode
from bella_rag.utils.openapi_util import count_tokens
from bella_rag.utils.schema_util import node_cache

logger = user_logger


@transaction.atomic
def add_chunk(source_id: str, source_name: str, content_title: str, content_data: str, chunk_type: str, chunk_pos: int,
              extra: dict):
    meta = {"source_id": source_id, "source_name": source_name, "node_type": chunk_type,
            "extra": _extra_data_from_dict_to_list(extra)}
    id_pos = ChunkContentAttachedService.find_max_id_pos(source_id) + 1
    node_id = source_id + '-' + str(id_pos)
    if chunk_type == NodeTypeEnum.TEXT.node_type_code:
        node = TextNode(id_=node_id, text=content_data, metadata=meta)
    elif chunk_type == NodeTypeEnum.IMAGE.node_type_code:
        node = ImageNode(id_=node_id, image_url=content_data, metadata=meta)
    elif chunk_type == NodeTypeEnum.QA.node_type_code:
        node = QaNode(id_=node_id, question_str=content_title, answer_str=content_data, metadata=meta)
    else:
        raise Exception('unknown chunk type')

    try:
        id_to_embed_map = embed_nodes([node], embed_model=embed_model)
        node.embedding = id_to_embed_map[node_id]
        # 更新插入位置之后节点的位置信息，为插入节点腾位置
        ChunkContentAttachedService.chunk_pos_increment(source_id, chunk_pos)
        ChunkContentAttachedService.save(convert_chunk_content_attached(chunk_pos, node))
        logger.info("add_chunk success chunk_id = %s [step=插入数据库]", node_id)
        vector_store.add([node])
        logger.info("add_chunk success chunk_id = %s [step=插入向量库]", node_id)
        es_store.add([node])
        logger.info("add_chunk success chunk_id = %s [step=插入es索引]", node_id)
        return node_id
    except Exception as e:
        logger.error("add_chunk failed: %s", str(e))
        # 手动回滚向量库数据
        try:
            vector_store.delete(ref_doc_id=node_id)
        except Exception as ve:
            logger.error("add_chunk rollback vector store failed: %s", str(ve))

        # 手动回滚Elasticsearch操作
        try:
            es_store.delete(ref_doc_id=node_id)
            logger.info("add_chunk rollback es_store for chunk_id = %s", node_id)
        except Exception as ee:
            logger.error("add_chunk rollback es store failed: %s", str(ee))

        raise


@transaction.atomic
def delete_chunk(chunk_id: str):
    # 【不完备】需要删除relationship
    chunk = ChunkContentAttachedService.get_by_chunk_id(chunk_id)
    deleted, _ = chunk.delete()
    if not deleted:
        raise ChunkOperateError('delete chunk failed')
    # update position
    ChunkContentAttachedService.chunk_pos_decrement(chunk.source_id, chunk.chunk_pos)
    logger.info("delete_chunk success chunk_id = %s [step=删除数据库]", chunk_id)
    vector_store.delete_documents([chunk_id])
    logger.info("delete_chunk success chunk_id = %s [step=删除向量库]", chunk_id)
    es_store.delete_nodes(node_ids=[chunk_id])
    logger.info("delete_chunk success chunk_id = %s [step=删除es索引]", chunk_id)

    # 删除缓存数据
    node_cache.remove(file_id=chunk.source_id)
    logger.info("delete_chunk cache success file_id = %s [step=清理缓存]", chunk.source_id)

    # 更新token量
    ChunkContentAttachedService.update_chunks_token(chunk.source_id, chunk.order_num,
                                                    -1 * count_tokens(chunk.content_data))


@transaction.atomic
def update_chunk(chunk_id: str, content_title: str, content_data: str, extra: dict):
    index = vector_store.query_by_ids([chunk_id])
    extend = ChunkContentAttachedService.get_by_chunk_id(chunk_id)
    if not index or not extend:
        raise ChunkOperateError('chunk not found: ' + chunk_id)
    # 若未传入切片内容，则保持原内容不更新
    if content_title or content_data:
        # 删除缓存数据
        node_cache.remove(file_id=extend.source_id)
        logger.info("delete_file success file_id = %s [step=清理缓存]", extend.source_id)

    origin_node = vector_store.doc2node(index[0], chunk_vector_index_structure)
    node = vector_store.doc2node(index[0], chunk_vector_index_structure)
    try:
        extend.content_title = content_title or extend.content_title
        extend.content_data = content_data or extend.content_data
        ChunkContentAttachedService.save(extend)
        logger.info("update_chunk success chunk_id = %s [step=更新数据库]", chunk_id)

        set_node_content(node, extend.content_title, extend.content_data)
        node.metadata[chunk_vector_index_structure.extra_key] = _extra_data_from_dict_to_list(extra)
        id_to_embed_map = embed_nodes([node], embed_model=embed_model)
        node.embedding = id_to_embed_map[node.node_id]
        vector_store.add([node])
        logger.info("update_chunk success chunk_id = %s [step=更新向量库]", chunk_id)

        es_store.add([node])
        logger.info("update_chunk success chunk_id = %s [step=更新es索引]", chunk_id)

        # 更新token量
        token_diff = count_tokens(content_data) - count_tokens(extend.content_data)
        ChunkContentAttachedService.update_chunks_token(extend.source_id, extend.order_num, token_diff)
    except Exception as e:
        logger.error("update_chunk failed: %s", str(e))
        # 手动回滚向量库数据
        try:
            vector_store.add([origin_node])
            logger.info("rollback update_chunk success chunk_id = %s [step=回滚向量库]", chunk_id)
        except Exception as ve:
            logger.error("update_chunk rollback vector store failed: %s", str(ve))

        try:
            es_store.add([origin_node])
            logger.info("rollback update_chunk success chunk_id = %s [step=回滚es索引]", chunk_id)
        except Exception as ee:
            logger.error("update_chunk rollback es store failed: %s", str(ee))

        raise


def chunk_list_by_ids(chunk_ids: List[str]) -> List[dict]:
    chunk_indexes = []
    batch = 900
    for batch_ids in [chunk_ids[i:i + batch] for i in range(0, len(chunk_ids), batch)]:
        chunk_indexes.extend(vector_store.query_by_ids(batch_ids))
    # list to dict
    chunk_indexes_map = {chunk_index['id']: chunk_index for chunk_index in chunk_indexes}
    chunk_extends = ChunkContentAttachedService.batch_get_by_chunk_ids(chunk_ids)
    return _merge_chunk_index_extend(chunk_indexes_map, chunk_extends)


def chunk_list_by_source_id(source_id: str, limit: int, offset: int, read_strong_consistency: bool):
    nodes = batch_query_by_source(source_id, limit, offset, read_strong_consistency)
    # list to dict
    chunk_indexes_map = {node.node_id: node.metadata for node in nodes}
    chunk_extends = ChunkContentAttachedService.batch_get_by_chunk_ids(list(chunk_indexes_map.keys()))
    return _merge_chunk_index_extend(chunk_indexes_map, chunk_extends)


def _merge_chunk_index_extend(chunk_indexes_map, chunk_extends):
    chunk_list = []
    for chunk_extend in chunk_extends:
        chunk_id = chunk_extend.chunk_id
        chunk = chunk_extend.to_dict()
        # merge chunk_index and chunk_extend
        index = chunk_indexes_map.get(chunk_id)
        if index:
            chunk['chunk_type'] = index[chunk_vector_index_structure.doc_type_key]
            chunk['extra'] = extract_metadata_from_extra(index[chunk_vector_index_structure.extra_key])
            chunk_list.append(chunk)
    return chunk_list
