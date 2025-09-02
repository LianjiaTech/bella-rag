from typing import List, Dict, Tuple, Optional

from llama_index.core import QueryBundle
from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core.callbacks import CallbackManager
from llama_index.core.constants import DEFAULT_SIMILARITY_TOP_K
from llama_index.core.llms.utils import LLMType
from llama_index.core.retrievers import QueryFusionRetriever as LlamaQueryFusionRetriever
from llama_index.core.retrievers.fusion_retriever import FUSION_MODES
from llama_index.core.schema import IndexNode

from bella_rag.schema.nodes import QaNode
from bella_rag.schema.nodes import StructureNode, NodeWithScore
from bella_rag.utils.trace_log_util import trace


class QueryFusionRetriever(LlamaQueryFusionRetriever):
    """
    需要实现一个QueryFusionRetriever，支持文档去重唯一键（源码里默认为text）
    """

    def __init__(
            self,
            retrievers: List[BaseRetriever],
            llm: Optional[LLMType] = None,
            query_gen_prompt: Optional[str] = None,
            mode: FUSION_MODES = FUSION_MODES.SIMPLE,
            similarity_top_k: int = DEFAULT_SIMILARITY_TOP_K,
            num_queries: int = 4,
            use_async: bool = True,
            verbose: bool = False,
            callback_manager: Optional[CallbackManager] = None,
            objects: Optional[List[IndexNode]] = None,
            object_map: Optional[dict] = None,
            retriever_weights: Optional[List[float]] = None,
    ) -> None:
        super().__init__(
            retrievers=retrievers,
            llm=llm, similarity_top_k=similarity_top_k,
            num_queries=num_queries, use_async=use_async,
            query_gen_prompt=query_gen_prompt,
            mode=mode, retriever_weights=retriever_weights,
            callback_manager=callback_manager,
            object_map=object_map,
            objects=objects,
            verbose=verbose,
        )

    def _reciprocal_rerank_fusion(
            self, results: Dict[Tuple[str, int], List[NodeWithScore]]
    ) -> List[NodeWithScore]:
        """
        Apply reciprocal rank fusion.

        The original paper uses k=60 for best results:
        https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
        """
        k = 60.0  # `k` is a parameter used to control the impact of outlier rankings.
        fused_scores = {}
        key_to_node = {}

        # compute reciprocal rank scores
        for nodes_with_scores in results.values():
            for rank, node_with_score in enumerate(
                    sorted(nodes_with_scores, key=lambda x: x.score or 0.0, reverse=True)
            ):
                key = self.get_node_unique_key(node_with_score)
                key_to_node[key] = node_with_score
                if key not in fused_scores:
                    fused_scores[key] = 0.0
                fused_scores[key] += 1.0 / (rank + k)

        # sort results
        reranked_results = dict(
            sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        )

        # adjust node scores
        reranked_nodes: List[NodeWithScore] = []
        for text, score in reranked_results.items():
            reranked_nodes.append(key_to_node[text])
            reranked_nodes[-1].score = score

        return reranked_nodes

    def _simple_fusion(
            self, results: Dict[Tuple[str, int], List[NodeWithScore]]
    ) -> List[NodeWithScore]:
        """Apply simple fusion."""
        # Use a dict to de-duplicate nodes
        all_nodes: Dict[str, NodeWithScore] = {}
        for nodes_with_scores in results.values():
            for node_with_score in nodes_with_scores:
                key = self.get_node_unique_key(node_with_score)
                if key in all_nodes:
                    max_score = max(node_with_score.score, all_nodes[key].score)
                    all_nodes[key].score = max_score
                else:
                    all_nodes[key] = node_with_score

        return sorted(all_nodes.values(), key=lambda x: x.score or 0.0, reverse=True)

    def get_node_unique_key(self, node: NodeWithScore) -> str:
        """
        获取节点唯一键，用作merge去重
        """
        return node.text


class SimilarQueryFusionRetriever(QueryFusionRetriever):

    def __init__(
            self,
            retrievers: List[BaseRetriever],
            similarity_top_k: int = DEFAULT_SIMILARITY_TOP_K,
            use_async: bool = False,
    ) -> None:
        self.similarity_top_k = similarity_top_k
        self.use_async = use_async
        self._retrievers = retrievers

    @trace(step="similar_fusion_retriever")
    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        queries: List[QueryBundle] = [query_bundle]

        if self.use_async:
            results = self._run_nested_async_queries(queries)
        else:
            results = self._run_sync_queries(queries)
        return self._similar_score_fusion(results)[: self.similarity_top_k]

    async def _aretrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        queries: List[QueryBundle] = [query_bundle]

        results = await self._run_async_queries(queries)
        return self._similar_score_fusion(results)[: self.similarity_top_k]

    def _similar_score_fusion(
            self, results: Dict[Tuple[str, int], List[NodeWithScore]]
    ) -> List[NodeWithScore]:
        all_nodes: Dict[str, NodeWithScore] = {}
        node_texts = set()
        for nodes_with_scores in results.values():
            for node_with_score in nodes_with_scores:
                if self.get_node_unique_key(node_with_score) in node_texts:
                    # 相同的node内容去重处理
                    continue
                if isinstance(node_with_score.node, QaNode):
                    """相似问合并"""
                    node_id = node_with_score.node.group_id
                    # 更新相同id分数更高的节点
                    all_nodes[node_id] = max(all_nodes.setdefault(node_id, node_with_score), node_with_score,
                                             key=lambda x: x.score or 0.0)
                else:
                    node_id = node_with_score.node_id
                    all_nodes[node_id] = node_with_score
                node_texts.add(self.get_node_unique_key(node_with_score))

        return sorted(all_nodes.values(), key=lambda x: x.score or 0.0, reverse=True)

    def get_node_unique_key(self, node: NodeWithScore) -> str:
        if isinstance(node.node, StructureNode):
            return node.node.get_complete_content() + node.node.order_num_str
        if isinstance(node.node, QaNode):
            return node.node.question_str + "\n" + node.node.answer_str
        return ''


class MultiRecallFusionRetriever(QueryFusionRetriever):

    def __init__(
            self,
            retrievers: List[BaseRetriever],
            llm: Optional[LLMType] = None,
            query_gen_prompt: Optional[str] = None,
            mode: FUSION_MODES = FUSION_MODES.SIMPLE,
            similarity_top_k: int = DEFAULT_SIMILARITY_TOP_K,
            num_queries: int = 4,
            use_async: bool = True,
            verbose: bool = False,
            callback_manager: Optional[CallbackManager] = None,
            objects: Optional[List[IndexNode]] = None,
            object_map: Optional[dict] = None,
            retriever_weights: Optional[List[float]] = None,
    ) -> None:
        super().__init__(
            retrievers=retrievers,
            llm=llm, similarity_top_k=similarity_top_k,
            num_queries=num_queries, use_async=use_async,
            query_gen_prompt=query_gen_prompt,
            mode=mode, retriever_weights=retriever_weights,
            callback_manager=callback_manager,
            object_map=object_map,
            objects=objects,
            verbose=verbose,
        )

    def get_node_unique_key(self, node: NodeWithScore) -> str:
        return node.unique_key

    def _get_queries(self, original_query: str) -> List[QueryBundle]:
        # 暂不通过模型提取关键词，由原始query进行检索
        return [QueryBundle(original_query)]

    def _reciprocal_rerank_fusion(
            self, results: Dict[Tuple[str, int], List[NodeWithScore]]
    ) -> List[NodeWithScore]:
        k = 60.0  # `k` is a parameter used to control the impact of outlier rankings.
        fused_scores = {}
        key_to_node = {}

        # compute reciprocal rank scores
        for nodes_with_scores in results.values():
            for rank, node_with_score in enumerate(
                    sorted(nodes_with_scores, key=lambda x: x.score or 0.0, reverse=True)
            ):
                key = self.get_node_unique_key(node_with_score)
                added_node = key_to_node.get(key)
                if added_node:
                    for attr in ['score', 'similarity_score', 'es_score']:
                        if hasattr(added_node, attr):
                            setattr(node_with_score, attr, getattr(added_node, attr))
                        # 某一路支持跳过rerank，则为所有节点赋予该属性
                        node_with_score.pass_rerank = node_with_score.pass_rerank or added_node.pass_rerank

                key_to_node[key] = node_with_score

                if key not in fused_scores:
                    fused_scores[key] = 0.0
                fused_scores[key] += 1.0 / (rank + k)

        # 暂不调整节点原始score，加权score仅做排序
        reranked_nodes: List[NodeWithScore] = []
        for text in sorted(fused_scores.items(), key=lambda x: x[1], reverse=True):
            rerank_node = key_to_node[text[0]]
            reranked_nodes.append(rerank_node)

        return reranked_nodes
