from typing import Optional, List

from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle

from app.services import ke_index_structure
from init.settings import user_logger
from ke_rag.llm.openapi import Rerank
from ke_rag.schema.nodes import BaseNode, StructureNode, QaNode
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
            rerank_score_map = {x.node_id: x.score for x in nodes[:self.top_k]}
        else:
            nodes = nodes[:max(self.rerank_num, self.top_k)]
            index_node_map = {i: n for i, n in enumerate(nodes)}
            docs = [n.node.get_complete_content() for n in nodes]

            rerank_resp = self.rerank.rerank(query_bundle.query_str, docs)
            rerank_score_map = {index_node_map[item["index"]].node_id: item["relevance_score"] for item in
                                rerank_resp.results}

        return self._rerank_and_sort_nodes(nodes, rerank_score_map)

    def _rerank_and_sort_nodes(self, nodes: List[NodeWithScore], rerank_score_map: dict) -> List[NodeWithScore]:
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
        complete_res = []
        for n in nodes:
            if n.node in complete_nodes:
                # 如果该检索节点已被补过，则去除该节点重新计算token补全
                nodes.remove(n)
                return self._complete(nodes, complete_nodes, chunk_max_len / len(nodes))
            # 只有有结构的node才能补全
            if isinstance(n.node, StructureNode):
                n.node.set_content(_small2big(n.node, chunk_max_len, complete_nodes, self.model))
            complete_res.append(n)
        return complete_res
