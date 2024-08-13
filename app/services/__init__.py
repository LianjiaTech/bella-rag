from app.schema.index import KeIndex
from init.settings import TENCENT_VECTOR_DB, OPENAPI
from ke_rag.llm.openapi import OpenAPIEmbedding

ak = OPENAPI["AK"]

ke_index_structure = KeIndex()

# todo 当前ke-embedding支持最大batch数量为10，后续切换模型调大限制
embed_model = OpenAPIEmbedding(model=TENCENT_VECTOR_DB["EMBEDDING_MODEL"], embedding_batch_size=10,
                               api_key=ak)