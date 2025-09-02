from llama_index.core.vector_stores import VectorStoreQuery, MetadataFilter, FilterOperator

from app.schema.index import ChunkVectorIndex
from app.services import ak, file_service
from app.services.index_extend.db_transformation import ChunkContentAttachedIndexExtend
from common.tool.vector_db_tool import vector_store
from init.settings import VECTOR_DB_COMMON
from bella_rag.llm.openapi import OpenAPIEmbedding
from bella_rag.utils.user_util import get_user_info
from bella_rag.vector_stores.types import MetadataFilters


def test_csv(test_file_id):
    # csv pass
    file_id = test_file_id('csv')
    file_service.file_indexing(file_id=file_id,
                               file_name=f'测试.csv',
                               metadata={"city_list": ["北京"]}, user=get_user_info())


def test_query(test_file_id):
    embed_model = OpenAPIEmbedding(model=VECTOR_DB_COMMON["EMBEDDING_MODEL"],
                                   embedding_batch_size=VECTOR_DB_COMMON["EMBEDDING_BATCH_SIZE"],
                                   api_key=ak, model_dimension=VECTOR_DB_COMMON["DIMENSION"])
    file_id = test_file_id('csv')
    file_service.file_indexing(file_id=file_id,
                               file_name=f'测试.csv',
                               metadata={"city_list": ["北京"]}, user=get_user_info())
    vq = VectorStoreQuery(query_embedding=embed_model.get_text_embedding(text='西红柿的颜色'))

    print(vector_store.query(vq, index=ChunkVectorIndex(), index_extend=ChunkContentAttachedIndexExtend()))

    # 过滤查询 source_id = doc_id
    vq = VectorStoreQuery(
        filters=MetadataFilters(
            filters=[MetadataFilter(key="source_id", value=[file_id],
                                    operator=FilterOperator.IN)]),
        query_embedding=embed_model.get_text_embedding(text='西红柿的颜色'),
        similarity_top_k=2)
    print(vector_store.query(vq, index=ChunkVectorIndex(), index_extend=ChunkContentAttachedIndexExtend()))

    vq = VectorStoreQuery(
        filters=MetadataFilters(filters=[MetadataFilter(key="extra", value=["doc_name:测试.csv"],
                                                        operator=FilterOperator.ANY)]),
        query_embedding=embed_model.get_text_embedding(text='西红柿的颜色'))
    print(vector_store.query(vq, index=ChunkVectorIndex(), index_extend=ChunkContentAttachedIndexExtend()))
    pass


def test_pdf(test_file_id):
    file_id = test_file_id('pdf')
    print(
        f'pdf result=${file_service.file_indexing(file_id=file_id, file_name="测试.pdf", metadata={}, user=get_user_info())}')


def test_docx(test_file_id):
    file_id = test_file_id('docx')
    print(
        f'docx result=${file_service.file_indexing(file_id=file_id, file_name="测试.docx", metadata={"city_list": ["北京"]}, user=get_user_info())}')


def test_md(test_file_id):
    file_id = test_file_id('md')
    print(
        f'md result=${file_service.file_indexing(file_id=file_id, file_name="测试.md", metadata={"city_list": ["北京"]}, user=get_user_info())}')


def test_html(test_file_id):
    file_id = test_file_id('html')
    print(
        f'html result=${file_service.file_indexing(file_id=file_id, file_name="测试.html", metadata={"city_list": ["北京"]}, user=get_user_info())}')


def test_txt(test_file_id):
    file_id = test_file_id('txt')
    print(
        f'txt result=${file_service.file_indexing(file_id=file_id, file_name="测试.txt", metadata={"city_list": ["北京"]}, user=get_user_info())}')
