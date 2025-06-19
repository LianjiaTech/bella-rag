from llama_index.core import VectorStoreIndex, StorageContext

from app.services import embed_model
from common.tool.es_db_tool import es_store
from common.tool.vector_db_tool import vector_store, questions_vector_store
from ke_rag.retrievals.retriever import EmptyRetriever

index = VectorStoreIndex(
    nodes=[],
    embed_model=embed_model,
    storage_context=StorageContext.from_defaults(vector_store=vector_store),
)

es_index = VectorStoreIndex(
    nodes=[],
    storage_context=StorageContext.from_defaults(vector_store=es_store),
)

question_index = VectorStoreIndex(
    nodes=[],
    embed_model=embed_model,
    storage_context=StorageContext.from_defaults(vector_store=questions_vector_store),
)

empty_retriever = EmptyRetriever()
