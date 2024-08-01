from typing import Optional, List

from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import NodeWithScore, QueryBundle


class RerankPostprocessor(BaseNodePostprocessor):
    """Rerank postprocessor."""

    def _postprocess_nodes(
            self,
            nodes: List[NodeWithScore],
            query_bundle: Optional[QueryBundle] = None,
    ) -> List[NodeWithScore]:
        """Postprocess nodes."""
        return nodes


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
