from typing import List

from django.db import transaction
from llama_index.core.indices.utils import embed_nodes

from app.services import question_vector_index_structure, embed_model
from app.services.question_answer_attached_service import QuestionAnswerIndexAttachedService
from app.strategy import es_store
from app.utils.convert import extract_metadata_from_extra, convert_question_answer_attached, \
    _extra_data_from_dict_to_list
from common.tool.vector_db_tool import batch_question_by_filter, questions_vector_store
from init.settings import user_logger
from bella_rag.schema.nodes import QaNode
from bella_rag.vector_stores.types import MetadataFilter, FilterOperator, MetadataFilters

logger = user_logger


@transaction.atomic
def add_qa_group(group_id: str, source_id: str, source_name: str, questions: List[str], answer: str, extra: dict):
    metadata = {'group_id': group_id, 'extra': _extra_data_from_dict_to_list(extra), 'source_id': source_id,
                'source_name': source_name}
    qa_nodes: List[QaNode] = []
    for question in questions:
        qa_nodes.append(QaNode(question_str=question,
                               answer_str=answer,
                               group_id=group_id,
                               metadata=metadata))
    question_id_to_embed_map = embed_nodes(qa_nodes, embed_model=embed_model)

    doc_ids = []
    try:
        for qa_node in qa_nodes:
            question_answer_attached = convert_question_answer_attached(qa_node)
            QuestionAnswerIndexAttachedService.save(question_answer_attached)
            qa_node.embedding = question_id_to_embed_map[qa_node.node_id]
            qa_node.id_ = question_answer_attached.id
            doc_ids.append(question_answer_attached.id)
        logger.info("update_question_answer success group_id = %s [step=更新数据库]", group_id)
        questions_vector_store.add(qa_nodes)
        logger.info("update_question_answer success group_id = %s [step=更新向量库]", group_id)
        es_store.add(qa_nodes)
        logger.info("update_question_answer success group_id = %s [step=更新es索引]", group_id)
        return [qa_node.node_id for qa_node in qa_nodes], group_id
    except Exception as e:
        logger.error("add_qa_group failed: %s", str(e))
        # 手动回滚向量库数据
        try:
            for doc_id in doc_ids:
                questions_vector_store.delete(ref_doc_id=doc_id)
        except Exception as ve:
            logger.error("add_qa_group rollback vector store failed: %s", str(ve))

        # 手动回滚Elasticsearch操作
        try:
            for doc_id in doc_ids:
                es_store.delete(ref_doc_id=doc_id)
            logger.info("add_qa_group rollback es_store for group_id = %s", group_id)
        except Exception as ee:
            logger.error("add_qa_group rollback es store failed: %s", str(ee))

        raise


@transaction.atomic
def delete_qa_by_group_id(group_id: str):
    delete_nodes = batch_question_by_filter('', 1, 0, [group_id], [], False)

    qas = QuestionAnswerIndexAttachedService.get_by_group_id(group_id)
    qa_ids = [qa.id for qa in qas]
    QuestionAnswerIndexAttachedService.delete_by_group_id(group_id)
    logger.info("delete_qa_by_group_id success chunk_id = %s [step=更新数库]", group_id)

    try:
        metadata_filter = MetadataFilter(operator=FilterOperator.IN, key="group_id", value=[group_id])
        questions_vector_store.delete_by_filter(MetadataFilters(filters=[metadata_filter]))
        logger.info("delete_qa_by_group_id success chunk_id = %s [step=更新向量库]", group_id)
        es_store.delete_nodes(node_ids=qa_ids)
        logger.info("delete_qa_by_group_id success chunk_id = %s [step=更新es索引]", group_id)
    except Exception as e:
        logger.error("delete_qa_by_group_id failed: %s", str(e))
        # 手动回滚向量库数据
        try:
            questions_vector_store.add(delete_nodes)
        except Exception as ve:
            logger.error("delete_qa_by_group_id rollback vector store failed: %s", str(ve))

        # 手动回滚Elasticsearch操作
        try:
            es_store.add(delete_nodes)
            logger.info("delete_qa_by_group_id rollback es_store for group_id = %s", group_id)
        except Exception as ee:
            logger.error("delete_qa_by_group_id rollback es store failed: %s", str(ee))
        raise


@transaction.atomic
def coverage_group(group_id: str, source_id: str, source_name: str, questions: List[str], answer: str, extra: dict):
    delete_qa_by_group_id(group_id=group_id)
    return add_qa_group(group_id=group_id,
                        source_id=source_id,
                        source_name=source_name,
                        questions=questions,
                        answer=answer,
                        extra=extra)


def qa_list(source_id: str, group_ids: List[str], qa_ids: List[str], limit: int, offset: int,
            read_strong_consistency: bool):
    qa_indexes = batch_question_by_filter(source_id=source_id, group_ids=group_ids, ids=qa_ids, limit=limit,
                                          offset=offset, read_strong_consistency=read_strong_consistency)
    # list to dict
    question_answer_indexes_map = {qa_index.node_id: qa_index.metadata for qa_index in qa_indexes}
    question_answer_extends = QuestionAnswerIndexAttachedService.batch_get_by_ids(
        list(question_answer_indexes_map.keys()))
    return _merge_question_answer_index_extend(question_answer_indexes_map, question_answer_extends)


def _merge_question_answer_index_extend(question_indexes_map, question_answer_extends):
    question_answer_list = []
    for question_answer_extend in question_answer_extends:
        db_id = question_answer_extend.id
        question_answer = question_answer_extend.to_dict()
        # merge chunk_index and chunk_extend
        index = question_indexes_map.get(str(db_id))
        extra = index.get(question_vector_index_structure.extra_key)
        question_answer['extra'] = extract_metadata_from_extra(extra)
        question_answer['source_name'] = index[question_vector_index_structure.doc_name_key]
        question_answer_list.append(question_answer)
    return question_answer_list
