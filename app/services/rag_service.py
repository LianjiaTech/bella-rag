from typing import List

import redis
from deprecated.sphinx import deprecated
from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core import StorageContext, VectorStoreIndex, QueryBundle, Settings
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
from app.services.index_extend.db_transformation import ChunkContentAttachedIndexExtend, \
    QuestionAnswerAttachedIndexExtend
from app.transformations.parser import BellaCsvParser
from app.utils.convert import build_annotation_from_score_node
from app.utils.convert import trans_metadata_to_extra
from common.handler.openapi_error_handler import mock_request_context
from common.tool.es_db_tool import es_store
from common.tool.redis_tool import redis_pool
from common.tool.vector_db_tool import questions_vector_store, chunk_index_extend, question_answer_extend
from common.tool.vector_db_tool import vector_store
from init.settings import OPENAPI, user_logger, RERANK, RETRIEVAL
from ke_rag import callback_manager
from ke_rag.callbacks.manager import register_callback
from ke_rag.handler import streaming_handler
from ke_rag.llm.openapi import OpenAPI, Rerank
from ke_rag.postprocessor.node import RerankPostprocessor, CompletePostprocessor, RebuildRelationPostprocessor
from ke_rag.preprocessor.ProcessorGenerators import StandardAnswerGenerator
from ke_rag.response_synthesizers.response_synthesizer_factory import get_llm_response_synthesizer
from ke_rag.retrievals.fusion_retrievel import QueryFusionRetriever
from ke_rag.retrievals.retriever import VectorIndexRetriever
from ke_rag.schema.nodes import BaseNode
from ke_rag.transformations.factory import TransformationFactory
from ke_rag.utils.file_util import get_file_type, get_file_name
from ke_rag.utils.trace_log_util import trace_context, trace
from ke_rag.vector_stores.index import VectorIndex
from ke_rag.vector_stores.types import MetadataFilters, MetadataFilter, FilterOperator
from ke_rag.vector_stores.vector_store import ManyVectorStoreIndex

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
    # todo 临时做去重，用于算法同学上传
    redis_key_prefix = "file_indexing_success_tmp_"
    redis_client = redis.Redis(connection_pool=redis_pool)

    has_done = redis_client.get(redis_key_prefix + file_id)
    if has_done:
        logger.info("文件已经上传完成，不需要再次上传 file_id = %s", file_id)
        return True
    # 设置UID到context，embedding请求会使用
    u_token = user_context.set(ucid)

    if callback:
        register_callback(callback)


    # 文件大小校验
    file = file_info(file_id)
    if file and int(file.get('bytes')) > 30000000:
        raise FileCheckException(f"文件大小超过30M：{file.get('bytes')}")

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
    knowledge_file_index_done_msg = {
        "file_id": file_id,
        "request_id": trace_context.get(),
        "file_path": file_path,
        "ucid": ucid}
    knowledge_file_index_done_producer.sync_send_message(json.dumps(knowledge_file_index_done_msg))
    user_logger.info(f'finish indexing file : {file_id}')
    redis_client.setex(redis_key_prefix + file_id, 86400, "done")



def async_file_indexing(file_id: str, file_path: str, metadata: dict, callback: str = None, ucid: str = None):
    thread = Thread(
        target=lambda: file_indexing(file_id=file_id, file_path=file_path, metadata=metadata, callback=callback,
                                     ucid=ucid))
    thread.start()


@deprecated(version='1.0', reason="旧版rag，协议优化后切换下线")
def rag(query: str,
        # 检索参数
        top_k: int = 3,
        file_ids: List[str] = None,
        score: float = 0.8,
        # 模型生成参数
        api_key: str = "",
        model: str = "c4ai-command-r-plus",
        instructions: str = "",
        top_p: int = 1,
        temperature: float = 0.01,
        max_tokens: int = None,
        metadata_filter: List[MetadataFilter] = [], ) -> ToolRagResponse:
    query_engine = build_rag_engine(query=query, top_k=top_k, file_ids=file_ids, score=score, api_key=api_key,
                                    model=model, instructions=instructions, metadata_filter=metadata_filter,
                                    top_p=top_p, temperature=temperature, max_tokens=max_tokens, stream=False)
    res = query_engine.query(query)
    response_data = DataItem(value=res.response,
                             annotations=build_annotation_from_score_node(res.source_nodes, ke_index_structure))
    return ToolRagResponse(data_items=[response_data])


# todo 后续rag协议切过来后,调整命名
def rag_v2(query: str,
           retrieval_param: dict,
           generate_param: dict,
           api_key: str = "") -> RagResponse:
    # 检索参数
    top_k = retrieval_param.get('top_k', 3)
    file_ids = retrieval_param.get('file_ids', [])
    score = retrieval_param.get('score', 0.8)
    metadata_filter = retrieval_param.get('metadata_filter', [])
    # 生成参数
    model = generate_param.get('model', 'c4ai-command-r-plus')
    instructions = generate_param.get('instructions', '')
    top_p = generate_param.get('top_p', 1)
    temperature = generate_param.get('temperature', 0.8)
    max_tokens = generate_param.get('max_tokens', None)

    query_engine = build_rag_engine(query=query, top_k=top_k, file_ids=file_ids, score=score, api_key=api_key,
                                    model=model, instructions=instructions, metadata_filter=metadata_filter,
                                    top_p=top_p, temperature=temperature, max_tokens=max_tokens, stream=False)
    res = query_engine.query(query)
    content = Content(index=0, type='text', text=Text(value=res.response,
                                                      annotations=build_annotation_from_score_node(res.source_nodes,
                                                                                                   ke_index_structure)))
    return RagResponse(content=[content])


@deprecated(version='1.0', reason="旧版rag，协议优化后切换下线")
def rag_streaming(
        query: str,
        # 检索参数
        top_k: int = 3,
        file_ids: List[str] = None,
        score: float = 0.8,
        # 模型生成参数
        api_key: str = "",
        model: str = "c4ai-command-r-plus",
        instructions: str = "",
        top_p: int = 1,
        temperature: float = 0.01,
        max_tokens: int = None,
        metadata_filter: List[MetadataFilter] = []):
    def yield_event(event: str, data: Any):
        yield f"event: {event}\n"
        yield f"data: {json.dumps(data.json_response(), ensure_ascii=False)}\n\n"

    query_engine = build_rag_engine(query=query, top_k=top_k, file_ids=file_ids, score=score, api_key=api_key,
                                    model=model, instructions=instructions, metadata_filter=metadata_filter,
                                    top_p=top_p, temperature=temperature, max_tokens=max_tokens, stream=True)

    streaming_response = query_engine.query(query)
    aid = str(uuid.uuid4())
    retrieval_send = False

    for text in streaming_response.response_gen:
        if not retrieval_send:
            annotation_event = streaming_handler.rag_annotation_event(
                id=aid,
                annotations=build_annotation_from_score_node(streaming_response.source_nodes, ke_index_structure)
            )
            retrieval_send = True
            user_logger.info(f"rag annotations: {annotation_event['data']}")
            yield from yield_event(annotation_event['event'], annotation_event['data'])

        msg_event = streaming_handler.rag_msg_event(id=aid, value=text)
        yield from yield_event(msg_event['event'], msg_event['data'])


# todo 后续rag协议切过来后,调整命名
def rag_streaming_v2(
        query: str,
        retrieval_param: dict,
        generate_param: dict,
        api_key: str = ""):
    # 检索参数
    top_k = retrieval_param.get('top_k', 3)
    file_ids = retrieval_param.get('file_ids', [])
    score = retrieval_param.get('score', 0.8)
    metadata_filter = retrieval_param.get('metadata_filter', [])
    # 生成参数
    model = generate_param.get('model', 'c4ai-command-r-plus')
    instructions = generate_param.get('instructions', '')
    top_p = generate_param.get('top_p', 1)
    temperature = generate_param.get('temperature', 0.8)
    max_tokens = generate_param.get('max_tokens', None)

    def yield_event(event: str, data: Any):
        yield f"event: {event}\n"
        yield f"data: {json.dumps(data.json_response(), ensure_ascii=False)}\n\n"

    query_engine = build_rag_engine(query=query, top_k=top_k, file_ids=file_ids, score=score, api_key=api_key,
                                    model=model, instructions=instructions, metadata_filter=metadata_filter,
                                    top_p=top_p, temperature=temperature, max_tokens=max_tokens, stream=True)

    streaming_response = query_engine.query(query)
    request_id = get_rag_request_id()
    aid = str(uuid.uuid4()) if not request_id else request_id
    retrieval_send = False

    llm_response = ""
    user_logger.info(f"rag request id: {request_id} start receive stream delta")
    for text in streaming_response.response_gen:
        user_logger.info(f"rag request id: {request_id} message delta: {text}")
        if not retrieval_send:
            retrieval_event = streaming_handler.create_rag_retrieval_event(
                id=aid,
                nodes=streaming_response.source_nodes,
                event_type='rag.retrieval.completed',
            )
            retrieval_send = True
            user_logger.info(f"rag annotations: {retrieval_event['data'].json_response()}")
            yield from yield_event(retrieval_event['event'], retrieval_event['data'])

        msg_delta_event = streaming_handler.create_rag_msg_event(id=aid, value=text, event_type='rag.message.delta')
        llm_response += text
        yield from yield_event(msg_delta_event['event'], msg_delta_event['data'])

    annotations = build_annotation_from_score_node(streaming_response.source_nodes, ke_index_structure)
    msg_complete_event = streaming_handler.create_rag_msg_event(id=aid, value=llm_response, annotations=annotations,
                                                                event_type='rag.message.completed')
    yield from yield_event(msg_complete_event['event'], msg_complete_event['data'])


def build_rag_engine(
        query: str,
        # 检索参数
        top_k: int = 3,
        file_ids: List[str] = None,
        score: float = 0.8,
        # 模型生成参数
        api_key: str = "",
        model: str = "c4ai-command-r-plus",
        instructions: str = "",
        top_p: int = 1,
        temperature: float = 0.01,
        max_tokens: int = None,
        metadata_filter: List[MetadataFilter] = [],
        stream: bool = False) -> RetrieverQueryEngine:
    user_logger.info(f"rag start, query : {query}, file_ids : {file_ids}")
    filters = [MetadataFilter(key="source_id", value=file_ids, operator=FilterOperator.IN)] if file_ids else []
    if metadata_filter:
        filters.extend(metadata_filter)
    metadata_filters = MetadataFilters(filters=filters)

    llm = OpenAPI(temperature=temperature, api_base=OPENAPI["URL"], api_key=api_key, timeout=300,
                  system_prompt=instructions, additional_kwargs={"top_p": top_p}, model=model)

    # 构建检索器
    # todo bypass传递有点深，可以加一个no return的retriever
    bypass_retrieve = not file_ids
    retriever = create_retriever_by_mode(metadata_filters=metadata_filters, bypass_retrieve=bypass_retrieve,
                                         score=score, retrieve_mode=retrieve_mode, plugins=plugins)

    # 根据提供插件构建后置处理器
    node_postprocessors = get_components_from_plugins(plugins, BaseNodePostprocessor)
    # 添加默认后置处理器
    node_postprocessors.extend(build_postprocessor_from_retrieve_param(score, top_k, retrieve_mode))

    # 构建多路检索器
    retriever = create_fusion_retriever(metadata_filters=metadata_filters,
                                        fusion_mode=FUSION_MODES.RECIPROCAL_RANK,
                                        score=score)
    response_synthesizer = get_llm_response_synthesizer(
        llm=llm,
        model=model,
        instruction=instructions,
        text_qa_template=bella_template,
        response_mode=ResponseMode.SIMPLE_SUMMARIZE,
        service_context=None,
    )

    # 根据提供插件构建后置处理器
    node_postprocessors = build_postprocessor_from_plugins(plugins, model=model)
    # 添加默认后置处理器
    node_postprocessors.extend([RerankPostprocessor(rerank=rerank, rerank_num=int(RERANK['RERANK_NUM']), top_k=top_k),
                                ScorePostprocessor(rerank_score_cutoff=score) if retrieve_mode == RetrievalMode.FUSION else ScorePostprocessor()])

    return RetrieverQueryEngine(
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


@trace("retrieval")
def retrieval(file_ids: List[str], query: str, top_k: int, max_tokens: int, score: float,
              metadata_filter: List[MetadataFilter]) -> FileRetrieve:
    user_logger.info(f"retrieval start, query : {query}, file_ids : {file_ids}, top_k : {top_k}")
    token = query_embedding_context.set([])
    file_ids = file_service.filter_deleted_files(file_ids)
    filters = [MetadataFilter(key="source_id", value=file_ids, operator=FilterOperator.IN)] if file_ids else []
    if metadata_filter:
        filters.extend(metadata_filter)
    metadata_filters = MetadataFilters(filters=filters)

    # 构建多路检索器
    retriever = create_fusion_retriever(metadata_filters=metadata_filters,
                                        fusion_mode=FUSION_MODES.RECIPROCAL_RANK,
                                        score=score)

    # 检索
    with callback_manager.as_trace("retrieve"):
        score_nodes = retriever._retrieve(query_bundle=QueryBundle(query_str=query))

    # 根据提供插件构建后置处理器
    node_postprocessors = build_postprocessor_from_plugins(plugins, model=DEFAULT_MODEL, max_tokens=max_tokens)
    # 添加默认后置处理器
    node_postprocessors.extend([RerankPostprocessor(rerank=rerank, rerank_num=int(RERANK['RERANK_NUM']), top_k=top_k),
                                ScorePostprocessor(rerank_score_cutoff=score) if retrieve_mode == RetrievalMode.FUSION else ScorePostprocessor()])

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
            content=score_node.get_content() if not isinstance(score_node.node,
                                                               BaseNode) else score_node.node.get_complete_content(),
            file_tag=score_node.node.get_node_type(),
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


# 构建混合检索器
def create_fusion_retriever(metadata_filters: MetadataFilters,
                            score: float,
                            fusion_mode: FUSION_MODES,) -> QueryFusionRetriever:
    retrievers = [
        create_base_vector_retriever(index, metadata_filters, {"index": ke_index_structure, "retrieve_vector": False,
                                                               "index_extend": chunk_index_extend}, score),
        create_base_vector_retriever(question_index, metadata_filters,
                                     {"index": ke_question_index_structure, "retrieve_vector": False,
                                      "index_extend": question_answer_extend},
                                     score)]

    vector_retriever = SimilarQueryFusionRetriever(retrievers=retrievers,
                                                   similarity_top_k=int(RETRIEVAL['RETRIEVAL_NUM']))

    es_retriever = create_base_vector_retriever(es_index, metadata_filters,
                                                {"index": es_index_structure, "index_extends": [chunk_index_extend,
                                                                                                question_answer_extend]},
                                                None)
    # 构建多路检索器
    return MultiRecallFusionRetriever(retrievers=[vector_retriever, es_retriever],
                                      similarity_top_k=int(RETRIEVAL['RETRIEVAL_NUM']),
                                      use_async=False,
                                      mode=fusion_mode)


# 构建基本向量检索器
def create_base_vector_retriever(vector_store_index: VectorStoreIndex,
                                 metadata_filters: MetadataFilters,
                                 vector_store_kwargs: dict,
                                 similarity_cutoff: float) -> BaseRetriever:
    return VectorIndexRetriever(
        index=vector_store_index,
        similarity_top_k=int(RETRIEVAL['RETRIEVAL_NUM']),
        filters=metadata_filters,
        vector_store_kwargs=vector_store_kwargs,
        similarity_cutoff=similarity_cutoff,
        rerank_threshold=float(RERANK['RERANK_THRESHOLD']),
    )


def get_rag_request_id():
    try:
        return trace_context.get()
    except Exception:
        # 上下文找不到trace_id则直接返回
        return None
