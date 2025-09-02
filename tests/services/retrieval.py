from llama_index.core import QueryBundle

from app.services import rag_service, question_vector_index_structure, chunk_vector_index_structure
from app.strategy.retrieval import index, question_index, _create_base_vector_retriever
from common.tool.vector_db_tool import chunk_index_extend, question_answer_extend
from bella_rag.retrievals.fusion_retriever import SimilarQueryFusionRetriever
from bella_rag.vector_stores.types import MetadataFilter, FilterOperator


def test_retrieval(test_file_id):
    test_file_types = ["txt", "pdf", "csv"]
    file_ids = []
    for test_file_type in test_file_types:
        file_ids.append(test_file_id(test_file_type))
    res = rag_service.retrieval(file_ids=file_ids,
                                query="西红柿的颜色", top_k=5, score=0,
                                metadata_filter=[],
                                plugins=[])
    assert len(res) > 0, "检索为空"
    first_item = res[0]
    assert first_item.metadata.get('source_id') in file_ids
    assert first_item.node.get_complete_content()


def test_async_fusion_retrieval(test_file_id):
    test_file_types = ["txt", "pdf", "csv"]
    file_ids = []
    for test_file_type in test_file_types:
        file_ids.append(test_file_id(test_file_type))
    filters = [
        MetadataFilter(key="source_id", value=file_ids, operator=FilterOperator.IN)]
    retrievers = [_create_base_vector_retriever(index, filters, chunk_vector_index_structure, chunk_index_extend,
                                                similarity_cutoff=0.4),
                  _create_base_vector_retriever(question_index, filters, question_vector_index_structure,
                                                question_answer_extend, similarity_cutoff=0.4)]
    query = QueryBundle(query_str='西红柿的颜色')

    sync_retriever = SimilarQueryFusionRetriever(retrievers=retrievers,
                                                 similarity_top_k=5, use_async=False)
    sync_result = sync_retriever._retrieve(query)

    async_retriever = SimilarQueryFusionRetriever(retrievers=retrievers,
                                                  similarity_top_k=5, use_async=True)
    async_result = async_retriever._retrieve(query)
    assert len(async_result) == len(sync_result)
    for i, node in enumerate(sync_result):
        assert node.node.get_complete_content() == async_result[i].node.get_complete_content()
