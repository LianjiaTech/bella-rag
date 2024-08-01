from typing import List

import requests
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.indices.vector_store import VectorIndexRetriever
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter

from app.prompts.rag import bella_template
from app.schema.index import KeIndex
from app.services.index_extend.db_transformation import ChunkContentAttachedIndexExtend
from app.utils.docx2pdf_util import convert_docx_to_pdf_in_memory
from common.tool.chubaofs_tool import ChuBaoFSTool
from common.tool.vector_db_tool import vector_store
from init.settings import OPENAPI, TENCENT_VECTOR_DB
from ke_rag.llm.openapi import OpenAPIEmbedding, OpenAPI
from ke_rag.postprocessor.node import RerankPostprocessor, CompletePostprocessor
from ke_rag.response_synthesizers.response_synthesizer_factory import get_llm_response_synthesizer
from ke_rag.transformations.factory import TransformationFactory
from ke_rag.utils.file_util import get_file_type, get_file_name

ak = OPENAPI["AK"]

embed_model = OpenAPIEmbedding(model=TENCENT_VECTOR_DB["EMBEDDING_MODEL"], embed_batch_size=1000,
                               api_key=ak)

# # todo：Q：system_prompt动态化怎么处理？A：LLMPredictor可以加载不同的system_prompt
llm = OpenAPI(temperature=0.01, api_base=OPENAPI["URL"], api_key=ak,
              system_prompt="这是system prompt")

index = VectorStoreIndex.from_vector_store(vector_store=vector_store, embed_model=embed_model)


def file_indexing(file_id: str, file_path: str, callback: str = None):
    '''
        1. Load file from filesystem
        2. reader file to Document
        3. Parse Document to BaseNode
        4. Indexing
    '''


def rag(query: str):
    # todo： 参数补充
    '''
        1. Parse query to BaseNode
        2. Indexing
    '''
    pass

    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=top_k,
        filters=metadata_filter,
        vector_store_kwargs={"index": KeIndex(), "index_extend": ChunkContentAttachedIndexExtend()},
    )

    response_synthesizer = get_llm_response_synthesizer(
        llm=llm,
        model=model,
        instruction=instructions,
        text_qa_template=bella_template,
        response_mode=ResponseMode.SIMPLE_SUMMARIZE,
        service_context=None,
    )

    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
        node_postprocessors=[SimilarityPostprocessor(similarity_cutoff=score),
                             CompletePostprocessor(chunk_max_length=_chunk_max_tokens(model_name=model,
                                                                                      system_prompt=instructions,
                                                                                      query=query),
                                                   model=model),
                             RerankPostprocessor()],
    )

    return query_engine.query(query)


def getDocumentMetadata(file_id: str, file_path: str):
    return {"source_id": file_id, "extra": [f"doc_name:{get_file_name(file_path)}"]}
