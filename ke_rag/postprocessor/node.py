from typing import Optional, List

from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle

from app.services import ke_index_structure
from init.settings import user_logger
from ke_rag.llm.openapi import Rerank
from ke_rag.schema.nodes import BaseNode, StructureNode, QaNode, NodeWithScore, ContextualNode, DocumentNodeRelationship
from ke_rag.utils.complete_util import small2big, Small2BigModes
from ke_rag.utils.schema_util import restore_relationships
from ke_rag.utils.trace_log_util import trace

logger = user_logger


class RerankPostprocessor(BaseNodePostprocessor):
    """Rerank postprocessor."""

    rerank: Rerank

    # rerank比较节点个数
    rerank_num: int = 20

    # 不走rerank的阈值
    rerank_threshold: float = 0.99

    def _postprocess_nodes(
            self,
            nodes: List[NodeWithScore],
            query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        """
        RerankPostprocessor nodes.
        rerank逻辑：
        1. 先按文件得分（文件内检索节点的最大分值）排序
        2. 按照节点的pos排序
        """
        if self.rerank is None or self._need_not_rerank(nodes):
            rerank_score_map = {}
            for i, node in enumerate(nodes):
                rerank_score_map[node.node_id] = -i
        else:
            nodes = nodes[:max(self.rerank_num, self.top_k)]
            index_node_map = {i: n for i, n in enumerate(nodes)}
            docs = [n.node.get_complete_content() for n in nodes]

            rerank_resp = self.rerank.rerank(query_bundle.query_str, docs)
            rerank_score_map = {index_node_map[item["index"]].node_id: item["relevance_score"] for item in
                                rerank_resp.results}

        return self._rerank_and_sort_nodes(nodes, rerank_score_map)

    def _rerank_and_sort_nodes(self, nodes: List[NodeWithScore], rerank_score_map: dict) -> List[NodeWithScore]:
        nodes = sorted(nodes, key=lambda x: rerank_score_map.get(x.node_id), reverse=True)
        rerank_score_map_new = {}
        file_index_map = {}
        for sindex, x in enumerate(nodes[:self.top_k]):
            if isinstance(x.node, QaNode):
                rerank_score_map_new[x.node_id] = [rerank_score_map.get(x.node_id), x.node.pos]
                continue
            doc_id = x.metadata[ke_index_structure.doc_id_key]
            if doc_id not in file_index_map:
                file_index_map[doc_id] = rerank_score_map.get(x.node_id)
            rerank_score_map_new[x.node_id] = [file_index_map[doc_id], x.node.pos]

        return sorted(nodes[:self.top_k],
                      key=lambda x: (-rerank_score_map_new[x.node_id][0], rerank_score_map_new[x.node_id][1]))

    def _need_not_rerank(self, nodes: List[NodeWithScore]) -> bool:
        """Check if rerank is needed."""
        if len(nodes) == 0 or nodes[0].score > self.rerank_threshold:
            return True
        return False


class CompletePostprocessor(BaseNodePostprocessor):
    """Complete postprocessor."""

    chunk_max_length: int

    model: str

    def _postprocess_nodes(
            self,
            nodes: List[NodeWithScore],
            query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        """Postprocess nodes."""
        return self._complete(nodes, complete_nodes=[], chunk_max_len=self.chunk_max_length)

    def _complete(self, nodes: List[NodeWithScore],
                  complete_nodes: List[BaseNode],  # 所有补过的节点列表，整体去重
                  chunk_max_len: int
                  ) -> List[NodeWithScore]:
        if not nodes:
            return []

        score_node_map = {node.node_id: (node, index) for index, node in enumerate(nodes)}
        complete_nodes = [node.node for node in nodes if isinstance(node.node, StructureNode)]
        res = [(node, index) for index, node in enumerate(nodes) if not isinstance(node.node, StructureNode)]

        for complete_node in complete_nodes:
            # 将上下文节点的score替换为检索到的分数最高的子节点score
            # 防止检索分数较低的上下文节点补全后无法进入top20 rerank
            if not isinstance(complete_node, ContextualNode):
                contextual_node = complete_node.doc_relationships.get(DocumentNodeRelationship.CONTEXTUAL)
                if contextual_node and contextual_node.node_id in score_node_map:
                    new_index = min(score_node_map[contextual_node.node_id][1],
                                    score_node_map[complete_node.node_id][1])
                    score_node_map[contextual_node.node_id] = (score_node_map[contextual_node.node_id][0], new_index)

        complete_res = small2big(complete_nodes, chunk_max_len, self.model, Small2BigModes.CONTEXT_MERGE)
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
        return res

    def _normalized_rerank_score(self, rerank_score: float):
        """对rerank分数做归一化"""
        normalized_score = (rerank_score + 10) / 20
        return max(0.0, min(1.0, normalized_score))

