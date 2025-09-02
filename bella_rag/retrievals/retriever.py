from typing import Optional, List, Any, Dict

from llama_index.core import VectorStoreIndex
from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.callbacks import CallbackManager
from llama_index.core.constants import DEFAULT_SIMILARITY_TOP_K
from llama_index.core.data_structs import IndexDict
from llama_index.core.indices.utils import log_vector_store_query_result
from llama_index.core.indices.vector_store import VectorIndexRetriever as LlamaVectorIndexRetriever
from llama_index.core.schema import ObjectType, QueryBundle, IndexNode
from llama_index.core.vector_stores.types import VectorStoreQueryMode, MetadataFilters, VectorStoreQueryResult

from bella_rag.schema.nodes import NodeWithScore
from bella_rag.utils.trace_log_util import trace
from bella_rag.vector_stores.elasticsearch import ElasticsearchStore


class VectorIndexRetriever(LlamaVectorIndexRetriever):

    similarity_cutoff: Optional[float] = None

    # 不走rerank的阈值
    rerank_threshold: Optional[float] = None

    def __init__(
            self,
            index: VectorStoreIndex,
            similarity_top_k: int = DEFAULT_SIMILARITY_TOP_K,
            vector_store_query_mode: VectorStoreQueryMode = VectorStoreQueryMode.DEFAULT,
            filters: Optional[MetadataFilters] = None,
            alpha: Optional[float] = None,
            node_ids: Optional[List[str]] = None,
            doc_ids: Optional[List[str]] = None,
            sparse_top_k: Optional[int] = None,
            callback_manager: Optional[CallbackManager] = None,
            object_map: Optional[dict] = None,
            embed_model: Optional[BaseEmbedding] = None,
            verbose: bool = False,
            similarity_cutoff: Optional[float] = None,
            rerank_threshold: Optional[float] = None,
            **kwargs: Any,
    ) -> None:
        """Initialize params."""
        self.similarity_cutoff = similarity_cutoff
        self.rerank_threshold = rerank_threshold
        super().__init__(
            callback_manager=callback_manager,
            object_map=object_map,
            verbose=verbose,
            index=index,
            embed_model=embed_model,
            similarity_top_k=similarity_top_k,
            vector_store_query_mode=vector_store_query_mode,
            alpha=alpha,
            node_ids=node_ids,
            doc_ids=doc_ids,
            filters=filters,
            sparse_top_k=sparse_top_k,
            **kwargs
        )

    @trace(step="retrieval")
    def _retrieve(
        self,
        query_bundle: QueryBundle,
    ) -> List[NodeWithScore]:
        return super()._retrieve(query_bundle)

    def _build_node_list_from_query_result(
        self, query_result: VectorStoreQueryResult
    ) -> List[NodeWithScore]:
        if query_result.nodes is None:
            # NOTE: vector store does not keep text and returns node indices.
            # Need to recover all nodes from docstore
            if query_result.ids is None:
                raise ValueError(
                    "Vector store query result should return at "
                    "least one of nodes or ids."
                )
            assert isinstance(self._index.index_struct, IndexDict)
            node_ids = [
                self._index.index_struct.nodes_dict[idx] for idx in query_result.ids
            ]
            nodes = self._docstore.get_nodes(node_ids)
            query_result.nodes = nodes
        else:
            # NOTE: vector store keeps text, returns nodes.
            # Only need to recover image or index nodes from docstore
            for i in range(len(query_result.nodes)):
                source_node = query_result.nodes[i].source_node
                if (not self._vector_store.stores_text) or (
                    source_node is not None and source_node.node_type != ObjectType.TEXT
                ):
                    node_id = query_result.nodes[i].node_id
                    if self._docstore.document_exists(node_id):
                        query_result.nodes[i] = self._docstore.get_node(
                            node_id
                        )  # type: ignore[index]

        log_vector_store_query_result(query_result)

        node_with_scores: List[NodeWithScore] = []
        for ind, node in enumerate(query_result.nodes):
            score = query_result.similarities[ind] if query_result.similarities is not None else None

            score_node = NodeWithScore(
                node=node,
                es_score=score if isinstance(self._index.vector_store, ElasticsearchStore) else None,
                score=score if not isinstance(self._index.vector_store, ElasticsearchStore) else None,
                similarity_score=score if not isinstance(self._index.vector_store, ElasticsearchStore) else None
            )

            if score_node.es_score:
                node_with_scores.append(score_node)
                continue

            if self.rerank_threshold and score_node.similarity_score \
                    and score_node.similarity_score >= self.rerank_threshold:
                score_node.pass_rerank = True

            # 分数前置过滤
            if self.similarity_cutoff is not None and score_node.similarity_score \
                    and score_node.similarity_score >= self.similarity_cutoff:
                node_with_scores.append(score_node)

        return node_with_scores


class EmptyRetriever(BaseRetriever):
    """空检索器，返回默认为空"""

    def __init__(
            self,
            callback_manager: Optional[CallbackManager] = None,
            object_map: Optional[Dict] = None,
            objects: Optional[List[IndexNode]] = None,
            verbose: bool = False,
    ) -> None:
        super().__init__(callback_manager, object_map, objects, verbose)

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        return []
