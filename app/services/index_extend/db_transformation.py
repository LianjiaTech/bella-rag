from typing import List, cast

from django.db import connections
from llama_index.core.schema import BaseNode

from app.services.chunk_content_attached_service import ChunkContentAttachedService
from app.services.question_answer_attached_service import QuestionAnswerIndexAttachedService
from app.utils.convert import convert_chunk_content_attached_list, convert_question_answer_index_attached_list
from common.helper.exception import CheckError
from init.settings import user_logger
from bella_rag.schema.nodes import StructureNode, QaNode
from bella_rag.schema.nodes import is_contextual_node, ImageNode
from bella_rag.transformations.index_extend.index_extend_transform_component import IndexExtendTransformComponent
from bella_rag.utils.trace_log_util import trace


class ChunkContentAttachedIndexExtend(IndexExtendTransformComponent):
    """
    因为数据安全问题腾讯向量库不允许保存content，所以增加此Service辅助向量化保存结果
    """

    @trace("build_recall_index")
    def build_recall_index(self, nodes: List[BaseNode]):
        # 使用 connections['default'] 来确保每次请求时新建数据库连接
        if not nodes:
            return nodes

        conn = connections['default']
        try:
            ChunkContentAttachedService.batch_save(convert_chunk_content_attached_list(nodes), connection=conn)
        except Exception as e:
            user_logger.error(f"build_recall_index batch save failed {e}")
            raise e
        finally:
            conn.close()

        return nodes

    def set_node_content(self, node: BaseNode):
        attached = ChunkContentAttachedService.get_by_chunk_id(node.node_id)
        set_node_content(node, attached.content_title, attached.content_data)
        return node

    @trace(step="batch_set_node_contents", log_enabled=False)
    def batch_set_node_contents(self, nodes: List[BaseNode]):
        ids = []
        res = []
        for node in nodes:
            ids.append(node.node_id)

        chunk_dict = {}
        for chunk in ChunkContentAttachedService.batch_get_by_chunk_ids(ids):
            chunk_dict[chunk.chunk_id] = chunk

        for node in nodes:
            chunk = chunk_dict.get(node.node_id)
            if chunk is None:
                user_logger.error(f'chunk set node contents error. chunk not found : {node.node_id}')
                continue
            set_node_content(node, chunk.content_title, chunk.content_data)
            node.pos = chunk.chunk_pos
            if not is_contextual_node(node):
                node.context_id = chunk.context_id
            if chunk.order_num:
                node.order_num_str = chunk.order_num

            if isinstance(node, StructureNode):
                node.token = chunk.token
            res.append(node)

        return res

    @trace(step="batch_set_node_contents", log_enabled=False)
    async def async_batch_set_node_contents(self, nodes: List[BaseNode]):
        ids = []
        res = []
        for node in nodes:
            ids.append(node.node_id)

        chunk_dict = {}
        async for chunk in ChunkContentAttachedService.async_batch_get_by_chunk_ids(ids):
            for item in chunk:  # 假设 chunk 是一个列表
                chunk_dict[item.chunk_id] = item

        for node in nodes:
            chunk = chunk_dict.get(node.node_id)
            if chunk is None:
                user_logger.error(f'chunk set node contents error. chunk not found : {node.node_id}')
                continue
            set_node_content(node, chunk.content_title, chunk.content_data)
            node.pos = chunk.chunk_pos
            node.context_id = chunk.context_id
            if chunk.order_num:
                node.order_num_str = chunk.order_num

            if isinstance(node, StructureNode):
                node.token = chunk.token
            res.append(node)

        return res

    def support_node_type(self):
        return StructureNode


class QuestionAnswerAttachedIndexExtend(IndexExtendTransformComponent):
    """
    因为数据安全问题腾讯向量库不允许保存content，所以增加此Service辅助向量化保存结果
    """

    @trace("build_recall_question_answer_index")
    def build_recall_index(self, nodes: List[BaseNode]):
        ids = QuestionAnswerIndexAttachedService.coverage_data(
            question_answer_attached_list=convert_question_answer_index_attached_list(nodes))
        # QuestionAnswer的需要赋值
        if len(ids) != len(nodes):
            user_logger.error("csv question 插入和实际node不一样！！！需要关注处理")
            raise CheckError(
                f"csv question 插入和实际node不一样！！！需要关注处理 source_id={nodes[0].metadata.get('source_id')}")
        # id赋值， embed赋值
        for i, node in enumerate(nodes):
            node.id_ = ids[i]
        return nodes

    def set_node_content(self, node: BaseNode):
        attached = QuestionAnswerIndexAttachedService.get_by_id(cast(int, node.node_id))
        set_node_content(node, attached.question, attached.answer)
        return node

    @trace(step="batch_set_node_contents", log_enabled=False)
    def batch_set_node_contents(self, nodes: List[BaseNode]):
        ids = []
        res = []
        for node in nodes:
            ids.append(int(node.node_id))

        attached_dict = {}
        for attached in QuestionAnswerIndexAttachedService.batch_get_by_ids_ignore_deleted(ids):
            attached_dict[attached.id] = attached

        for i in range(len(nodes)):
            attached = attached_dict.get(int(nodes[i].node_id))
            if attached is None:
                user_logger.error(f'qa set node contents error. attach not found : {nodes[i].node_id}')
                nodes[i].question_str = ''
                nodes[i].answer_str = ''
                continue
            nodes[i].group_id = attached.group_id
            nodes[i].question_str = attached.question
            nodes[i].answer_str = attached.answer
            res.append(nodes[i])

        return res

    @trace(step="batch_set_node_contents", log_enabled=False)
    async def async_batch_set_node_contents(self, nodes: List[BaseNode]):
        ids = []
        res = []
        for node in nodes:
            ids.append(node.node_id)

        attached_dict = {}
        async for attached in QuestionAnswerIndexAttachedService.async_batch_get_by_ids_ignore_deleted(ids):
            for attach in attached:
                attached_dict[attach.id] = attach

        for i in range(len(nodes)):
            attached = attached_dict.get(int(nodes[i].node_id))
            if attached is None:
                user_logger.error(f'qa set node contents error. attach not found : {nodes[i].node_id}')
                continue
            nodes[i].group_id = attached.group_id
            nodes[i].question_str = attached.question
            nodes[i].answer_str = attached.answer
            res.append(nodes[i])
        return res

    def support_node_type(self):
        return QaNode


def set_node_content(node: BaseNode, title, data):
    title = "" if not title else title
    data = "" if not data else data
    if isinstance(node, QaNode):
        node.set_qa(title, data)
    elif isinstance(node, ImageNode):
        node.image_url = data
        ocr_result = title
        if title == data:
            # 兼容历史文件图片未解析（即title也为图片url）的问题
            ocr_result = ""
        node.image_ocr_result = ocr_result
    else:
        node.set_content(data)
    return node
