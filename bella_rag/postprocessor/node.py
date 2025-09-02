import random
import time
from typing import Optional, List, Callable

from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import QueryBundle

from app.services import chunk_vector_index_structure
from app.common.contexts import TraceContext
from init.settings import user_logger
from bella_rag.llm.openapi import Rerank
from bella_rag.schema.nodes import StructureNode, QaNode, NodeWithScore, \
    DocumentNodeRelationship, is_contextual_node, ImageNode, MetadataMode
from bella_rag.utils.complete_util import small2big, Small2BigModes
from bella_rag.utils.schema_util import restore_relationships
from bella_rag.utils.trace_log_util import trace

logger = user_logger


class RerankPostprocessor(BaseNodePostprocessor):
    """Rerank postprocessor."""

    rerank: Optional[Rerank] = None

    # rerank比较节点个数
    rerank_num: int = 20

    top_k: int = 3

    @trace("rerank_processor")
    def _postprocess_nodes(
            self,
            nodes: List[NodeWithScore],
            query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        if TraceContext.is_mock_request:
            mock_time = random.uniform(0.1, 1)
            user_logger.info(f'mock request rerank, mock time:{mock_time}')
            time.sleep(mock_time)
            return nodes
        """
        RerankPostprocessor nodes.
        rerank逻辑：
        1. 先按文件得分（文件内检索节点的最大分值）排序
        2. 按照节点的pos排序
        """
        try:
            if self.rerank is None or self._need_not_rerank(nodes):
                rerank_score_map = {}
                nodes = sorted(nodes, key=lambda x: x.score if x.score else 0, reverse=True)
                for i, node in enumerate(nodes):
                    rerank_score_map[node.node_id] = -i
                return self._rerank_and_sort_nodes(nodes, rerank_score_map)
            else:
                nodes = nodes[:max(self.rerank_num, self.top_k)]
                index_node_map = {i: n for i, n in enumerate(nodes)}
                docs = [n.node.get_complete_content(MetadataMode.RERANK) for n in nodes]

                rerank_resp = self.rerank.rerank(query_bundle.query_str, docs)
                rerank_score_map = {index_node_map[item["index"]].node_id: item["relevance_score"] for item in
                                    rerank_resp.results}
                rerank_nodes = self._rerank_and_sort_nodes(nodes, rerank_score_map)
                for node in rerank_nodes:
                    # 补充rerank分数
                    node.rerank_score = rerank_score_map.get(node.node_id)
                return rerank_nodes
        except Exception as e:
            user_logger.error(f'rerank failed: {str(e)}')
            return nodes

    def _rerank_and_sort_nodes(self, nodes: List[NodeWithScore], rerank_score_map: dict) -> List[NodeWithScore]:
        nodes = sorted(nodes, key=lambda x: rerank_score_map.get(x.node_id), reverse=True)
        rerank_score_map_new = {}
        file_index_map = {}
        for sindex, x in enumerate(nodes[:self.top_k]):
            if isinstance(x.node, QaNode):
                rerank_score_map_new[x.node_id] = [rerank_score_map.get(x.node_id), x.node.pos]
                continue
            doc_id = x.metadata[chunk_vector_index_structure.doc_id_key]
            if doc_id not in file_index_map:
                file_index_map[doc_id] = rerank_score_map.get(x.node_id)
            rerank_score_map_new[x.node_id] = [file_index_map[doc_id], x.node.pos]

        return sorted(nodes[:self.top_k],
                      key=lambda x: (-rerank_score_map_new[x.node_id][0], rerank_score_map_new[x.node_id][1]))

    def _need_not_rerank(self, nodes: List[NodeWithScore]) -> bool:
        """Check if rerank is needed."""
        if len(nodes) == 0:
            return True
        for node in nodes:
            if node.pass_rerank:
                return True
        return False


class CompletePostprocessor(BaseNodePostprocessor):
    """Complete postprocessor."""

    chunk_max_length: int

    model: str = 'gpt-4o'

    small2big_strategy: Small2BigModes

    @trace("complete_processor")
    def _postprocess_nodes(
            self,
            nodes: List[NodeWithScore],
            query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        """Postprocess nodes."""
        return self._complete(nodes, chunk_max_len=self.chunk_max_length)

    def _complete(self, nodes: List[NodeWithScore], chunk_max_len: int) -> List[NodeWithScore]:
        if not nodes:
            return []

        score_node_map = {node.node_id: (node, index) for index, node in enumerate(nodes)}
        complete_nodes = [node.node for node in nodes if isinstance(node.node, StructureNode)]
        res = [(node, index) for index, node in enumerate(nodes) if not isinstance(node.node, StructureNode)]

        for complete_node in complete_nodes:
            # 将上下文节点的score替换为检索到的分数最高的子节点score
            # 防止检索分数较低的上下文节点补全后无法进入top20 rerank
            if not is_contextual_node(complete_node):
                contextual_node = complete_node.doc_relationships.get(DocumentNodeRelationship.CONTEXTUAL)
                if contextual_node and contextual_node.node_id in score_node_map:
                    new_index = min(score_node_map[contextual_node.node_id][1],
                                    score_node_map[complete_node.node_id][1])
                    score_node_map[contextual_node.node_id] = (score_node_map[contextual_node.node_id][0], new_index)

        complete_res = small2big(complete_nodes, chunk_max_len, self.model, self.small2big_strategy)
        for node in complete_res:
            score_node, original_index = score_node_map[node.node_id]
            score_node.node = node
            res.append((score_node, original_index))

        res.sort(key=lambda x: x[1])
        return [node for node, _ in res]


class RebuildRelationPostprocessor(BaseNodePostprocessor):
    """RebuildRelation postprocessor."""

    @trace(step="rebuild_relations", log_enabled=False)
    def _postprocess_nodes(
            self,
            nodes: List[NodeWithScore],
            query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        """Postprocess nodes."""
        # 还原节点relation关系
        restore_relationships(nodes=nodes)
        return nodes


class ScorePostprocessor(BaseNodePostprocessor):
    """节点score处理器"""
    rerank_score_cutoff: Optional[float] = None
    top_k: int = 3

    def _postprocess_nodes(
            self,
            nodes: List[NodeWithScore],
            query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        """Postprocess nodes."""
        res = []
        for node in nodes:
            node.score = node.score or 0
            if self.rerank_score_cutoff and node.rerank_score:
                normalized_score = self._normalized_rerank_score(node.rerank_score)
                node.score = normalized_score
                if normalized_score > self.rerank_score_cutoff:
                    res.append(node)
            else:
                res.append(node)
        return res[:self.top_k]

    def _normalized_rerank_score(self, rerank_score: float):
        """对rerank分数做归一化"""
        normalized_score = (rerank_score + 10) / 20
        return max(0.0, min(1.0, normalized_score))


class ImageOcrPostprocessor(BaseNodePostprocessor):
    """图片ocr内容加工 postprocessor."""
    # 图片ocr识别
    image_ocr_recognize: bool = False
    image_url_signer: Optional[Callable[[str], str]] = None

    def _postprocess_nodes(
            self,
            nodes: List[NodeWithScore],
            query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        """Postprocess nodes."""
        if not self.image_ocr_recognize:
            for node in nodes:
                if isinstance(node.node, StructureNode):
                    # 非ocr解析模式，则将group里的image节点ocr结果清空
                    new_complete_group_nodes = []
                    for complete_group_node in node.node.get_complete_group_nodes():
                        if isinstance(complete_group_node, ImageNode):
                            new_complete_group_nodes.append(
                                ImageNode(id_=complete_group_node.node_id, text=complete_group_node.text,
                                          image_ocr_result="", image_url=complete_group_node.image_url,
                                          pos=complete_group_node.pos, token=complete_group_node.token,
                                          order_num_str=complete_group_node.order_num_str,
                                          metadata=complete_group_node.metadata,
                                          context_id=complete_group_node.context_id))
                        else:
                            new_complete_group_nodes.append(complete_group_node)
                    node.node.doc_relationships[DocumentNodeRelationship.COMPLETE_GROUP] = set(new_complete_group_nodes)

        for node in nodes:
            if isinstance(node.node, StructureNode):
                for complete_group_node in node.node.get_complete_group_nodes():
                    if isinstance(complete_group_node, ImageNode):
                        old_image_url = complete_group_node.image_url
                        signed_image_url = self.image_url_signer(old_image_url) if self.image_url_signer else old_image_url
                        node.node.text = node.node.text.replace(old_image_url, signed_image_url)
                        complete_group_node.image_url = signed_image_url

        return nodes
