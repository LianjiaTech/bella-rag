from typing import List

import requests
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.indices.vector_store import VectorIndexRetriever
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter

from app.controllers.response.tool_rag_response import FileItem, FileRetrieve, Content, Text, \
    RagResponse, DataItem, ToolRagResponse
from app.prompts.rag import get_rag_template
from app.services import ke_index_structure, embed_model
from app.services.chunk_content_attached_service import ChunkContentAttachedService
from app.services.index_extend.db_transformation import ChunkContentAttachedIndexExtend
from app.utils.docx2pdf_util import convert_docx_to_pdf_in_memory
from common.tool.chubaofs_tool import ChuBaoFSTool
from common.tool.vector_db_tool import vector_store
from init.settings import OPENAPI, TENCENT_VECTOR_DB
from ke_rag.llm.openapi import OpenAPIEmbedding, OpenAPI
from ke_rag.postprocessor.node import RerankPostprocessor, CompletePostprocessor
from ke_rag.response_synthesizers.response_synthesizer_factory import get_llm_response_synthesizer
from ke_rag.schema.nodes import BaseNode
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

    redis_client = redis.Redis(connection_pool=redis_pool)
    redis_key_prefix = "file_indexing_success_wyk_"
    has_done = redis_client.get(redis_key_prefix + file_id)
    if has_done:
        logger.info("已经消费完成，不需要再次消费 file_id = %s", file_id)
        return

    if callback:
        register_callback(callback)


    user_logger.info(f'start indexing file : {file_id}, path : {file_path}, city_list:{city_list}')
    chubao = ChuBaoFSTool()
    stream = chubao.read_file(file_path)
    file_type = get_file_type(file_path)

    # docx文件转为pdf处理（短期内）
    if file_type in ["doc", "docx"]:
        stream = convert_docx_to_pdf_in_memory(stream)
        file_type = "pdf"
    # csv中的cityList等元素从条目中获取
    if file_type == "csv":
        city_list = []

    documents = TransformationFactory.get_reader(file_type).load_data(stream)

    transforms = []
    storage_context = None
    # 先这样分叉，以后看llamaIndex有没有提供更好的方式
    if file_type == "csv":
        storage_context = StorageContext.from_defaults(vector_store=questions_vector_store)
        transforms = [BellaCsvParser(file_id=file_id), QuestionAnswerAttachedIndexExtend()]
    else:
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        transforms = [TransformationFactory.get_parser(file_type=file_type),
                      ChunkContentAttachedIndexExtend()]

    ManyVectorStoreIndex.from_documents(
        documents, storage_context=storage_context, transformations=transforms, embed_model=embed_model,
        metadata=getDocumentMetadata(file_id=file_id, file_path=file_path, city_list=city_list)
    )

    # 发送文件处理完成的消息
    from app.workers import knowledge_file_index_done_producer
    knowledge_file_index_done_msg = {"file_id": file_id, "request_id": trace_context.get(), "file_path": file_path}
    knowledge_file_index_done_producer.sync_send_message(json.dumps(knowledge_file_index_done_msg))
    user_logger.info(f'finish indexing file : {file_id}')


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
                             RebuildRelationPostprocessor(),
                             CompletePostprocessor(chunk_max_length=RETRIEVAL['COMPLETE_MAX_TOKEN'],
                                                   model=model),
                             RerankPostprocessor(rerank=rerank, rerank_num=20, rerank_threshold=0.99, top_k=top_k)],
    )


def getDocumentMetadata(file_id: str, file_path: str, city_list: List):
    extra = []
    if city_list:
        for city in city_list:
            extra.append(f"city_list:{city}")
    return {"source_id": file_id, "source_name": get_file_name(file_path), "extra": extra}


def retrieval(file_ids: List[str], query: str, top_k: int, max_tokens: int) -> FileRetrieve:
    user_logger.info(f"retrieval start, query : {query}, file_ids : {file_ids}, top_k : {top_k}")
    metadata_filter = MetadataFilters(
        filters=[MetadataFilter(key="source_id", value=file_ids, operator=FilterOperator.IN)])

    retrievers = [create_base_vector_retriever(index, metadata_filters, chunk_index_extend),
                  create_base_vector_retriever(question_index, metadata_filters, question_answer_extend)]

    retriever = SimilarQueryFusionRetriever(retrievers=retrievers,
                                            similarity_top_k=int(RETRIEVAL['RETRIEVAL_NUM']))

    # 检索
    score_nodes = retriever._retrieve(query_bundle=QueryBundle(query_str=query))

    node_postprocessors = [SimilarityPostprocessor(similarity_cutoff=score),
                           RebuildRelationPostprocessor(),
                           CompletePostprocessor(chunk_max_length=max_tokens, model="gpt-4"),
                           RerankPostprocessor(rerank=rerank, rerank_num=int(RERANK['RERANK_NUM']),
                                               rerank_threshold=float(RERANK['RERANK_THRESHOLD']),
                                               top_k=top_k)]

    for postprocessor in node_postprocessors:
        score_nodes = postprocessor.postprocess_nodes(nodes=score_nodes, query_str=query)

    # 补全, 默认token数
    complete = CompletePostprocessor(chunk_max_length=max_tokens, model="gpt-4")
    nodes = complete.postprocess_nodes(nodes=nodes, query_str=query)
    items = []
    for score_node in nodes:
        item = FileItem(
            id=score_node.node_id,
            file_id=score_node.metadata[ke_index_structure.doc_id_key],
            file_name=score_node.metadata[ke_index_structure.doc_name_key],
            score=score_node.score,
            chunk_id=score_node.node_id,
            content=score_node.get_content() if not isinstance(score_node.node, BaseNode) else score_node.node.get_complete_content(),
            file_tag=score_node.metadata[ke_index_structure.doc_type_key]
        )
        items.append(item)

    res = FileRetrieve(id=str(uuid.uuid4()), created_at=int(time.time()), object="file_retrieve", list=items)
    user_logger.info(f"retrieval result : {json.dumps(res.to_dict(), ensure_ascii=False)}")
    return res


def delete_file(file_id: str) -> None:
    user_logger.info(f'start delete file : {file_id}')
    # 删除mysql数据
    deleted, _ = ChunkContentAttachedMapper.delete_by_source_id(source_id=file_id)
    if not deleted:
        # todo: 细分一下异常？
        raise Exception(f"delete file {file_id} failed")
    # 删除向量库数据
    vector_store.delete(ref_doc_id=file_id, delete_key=ke_index_structure.doc_id_key)


def rename_file(file_id: str, file_name: str):
    user_logger.info(f'start rename file : {file_id} to {file_name}')
    # 1. 更新向量库的标量字段
    doc = Document()
    doc.__dict__[ke_index_structure.doc_name_key] = file_name
    condition = "source_id=\"{}\"".format(file_id)
    vector_filter = Filter(cond=condition)
    vector_store.collection.update(data=doc, filter=vector_filter)