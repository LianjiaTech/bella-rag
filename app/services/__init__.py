from app.schema.index import KeIndex
from init.settings import TENCENT_VECTOR_DB, OPENAPI
from ke_rag.llm.openapi import OpenAPIEmbedding

ak = OPENAPI["AK"]

ke_index_structure = KeIndex()

embed_model = OpenAPIEmbedding(model=TENCENT_VECTOR_DB["EMBEDDING_MODEL"], embedding_batch_size=100,
                               api_key=ak)
