from llama_index.core.vector_stores import VectorStoreQuery

from common.tool.vector_db_tool import vector_store
from app.services.index_extend.db_transformation import ChunkContentAttachedIndexExtend
from app.schema.index import ChunkVectorIndex
from app.services import embed_model


def test_tencent_vector_store_query():
    query_str = "西红柿的颜色"
    embedding = embed_model.get_text_embedding(text=query_str)
    query = VectorStoreQuery(
        query_embedding=embedding,
        query_str=query_str,
    )
    vector_store.query(query=query, index=ChunkVectorIndex(), index_extend=ChunkContentAttachedIndexExtend(), retrieve_vector=False)
