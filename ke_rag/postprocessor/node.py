from typing import Optional, List

from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle


class RerankPostprocessor(BaseNodePostprocessor):
    """Rerank postprocessor."""

    rerank: Rerank

    # 不走rerank的阈值
    rerank_threshold: float = 0.99

    def _postprocess_nodes(
            self,
            nodes: List[NodeWithScore],
            query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        """Postprocess nodes."""
        if self.rerank is None or self._need_not_rerank(nodes):
            return nodes
        index_node_map = {}
        docs = []
        for i, n in enumerate(nodes):
            index_node_map[i] = n
            docs.append(n.node.get_content())

        rerank_resp = self.rerank.rerank(query_bundle.query_str, docs)
        rerank_items = rerank_resp.results
        # 更新节点重排后的score
        for item in rerank_items:
            index_node_map[item.index].score = item.relevance_score
        # 重新排序
        nodes = sorted(nodes, key=lambda x: x.score, reverse=True)
        return nodes

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
