from app.schema.index import ChunkVectorIndex, QuestionVectorIndex
from app.schema.index import EsIndex
from init.settings import OPENAPI, VECTOR_DB_COMMON, RETRIEVAL
from bella_rag.llm.api_call_mode import BILLING_TRANSFER_MODE, DIRECT_CALL_MODE
from bella_rag.llm.openapi import OpenAPIEmbedding

ak = OPENAPI["AK"]
EXTRA_DOC_TYPE_KEY = 'doc_type'

chunk_vector_index_structure = ChunkVectorIndex()
es_index_structure = EsIndex()

question_vector_index_structure = QuestionVectorIndex()

file_index_embed_model = OpenAPIEmbedding(
    model=VECTOR_DB_COMMON.get("EMBEDDING_MODEL"),
    embedding_batch_size=VECTOR_DB_COMMON["EMBEDDING_BATCH_SIZE"],
    api_key=OPENAPI["BILLING_TRANSFER_API_KEY"],
    model_dimension=int(VECTOR_DB_COMMON["DIMENSION"]),
    call_mode=BILLING_TRANSFER_MODE,
    service_client=OPENAPI["BILLING_TRANSFER_SERVICE_CLIENT"],
)

direct_embed_model = OpenAPIEmbedding(
    model=VECTOR_DB_COMMON.get("EMBEDDING_MODEL"),
    embedding_batch_size=VECTOR_DB_COMMON["EMBEDDING_BATCH_SIZE"],
    api_key=ak,
    model_dimension=int(VECTOR_DB_COMMON["DIMENSION"]),
    call_mode=DIRECT_CALL_MODE,
)

retrieval_embed_model = OpenAPIEmbedding(
    model=VECTOR_DB_COMMON.get("EMBEDDING_MODEL"),
    embedding_batch_size=VECTOR_DB_COMMON["EMBEDDING_BATCH_SIZE"],
    api_key=ak,
    model_dimension=int(VECTOR_DB_COMMON["DIMENSION"]),
    timeout=RETRIEVAL["EMBEDDING_TIMEOUT"],
    call_mode=DIRECT_CALL_MODE,
)
