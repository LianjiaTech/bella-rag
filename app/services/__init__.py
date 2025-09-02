from app.schema.index import ChunkVectorIndex, QuestionVectorIndex
from app.schema.index import EsIndex
from init.settings import OPENAPI, VECTOR_DB_COMMON
from bella_rag.llm.openapi import OpenAPIEmbedding

ak = OPENAPI["AK"]
EXTRA_DOC_TYPE_KEY = 'doc_type'

chunk_vector_index_structure = ChunkVectorIndex()
es_index_structure = EsIndex()

question_vector_index_structure = QuestionVectorIndex()

embed_model = OpenAPIEmbedding(
    model=VECTOR_DB_COMMON.get("EMBEDDING_MODEL"),
    embedding_batch_size=VECTOR_DB_COMMON["EMBEDDING_BATCH_SIZE"],
    api_key=ak,
    model_dimension=int(VECTOR_DB_COMMON["DIMENSION"])
)
