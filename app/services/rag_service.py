import random
import string
import time
import uuid
from typing import List

from llama_index.core import QueryBundle, Response
from llama_index.core.base.llms.types import ChatResponse
from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import ResponseMode
from openai import APIError
from openai._types import Headers

from app import openapi_trace_handler as trace_handler
from app.common.contexts import query_embedding_context, UserContext, TraceContext
from app.controllers import default_event_handler
from app.plugin.factory import build_postprocessor_from_retrieve_param, \
    get_components_from_plugins
from app.plugin.plugins import Plugin
from app.prompts.rag import get_rag_template
from app.services import file_service
from app.strategy.retrieval import RetrievalMode, create_retriever_by_mode
from init.settings import OPENAPI, user_logger, RETRIEVAL
from bella_rag import callback_manager
from bella_rag.handler.streaming_handler import BaseEventHandler, RAGStreamingHandler
from bella_rag.llm.openapi import OpenAPI
from bella_rag.llm.types import Sensitive
from bella_rag.preprocessor.ProcessorGenerators import StandardAnswerGenerator
from bella_rag.response_synthesizers.response_synthesizer_factory import get_llm_response_synthesizer
from bella_rag.schema.nodes import NodeWithScore
from bella_rag.utils.openapi_util import MOCK_MODEL
from bella_rag.utils.trace_log_util import trace
from bella_rag.vector_stores.types import MetadataFilters

logger = user_logger


def rag(query: str,
        top_k: int = 3,
        file_ids: List[str] = None,
        score: float = 0,
        api_key: str = "",
        model: str = "c4ai-command-r-plus",
        instructions: str = "",
        top_p: int = 1,
        temperature: float = 0.01,
        max_tokens: int = None,
        metadata_filters: MetadataFilters = None,
        retrieve_mode: RetrievalMode = RetrievalMode.SEMANTIC,
        plugins: List[Plugin] = None,
        show_quote: bool = False,
        event_handler: BaseEventHandler = default_event_handler):
    token = query_embedding_context.set([])
    file_ids = file_service.filter_deleted_files(file_ids)
    query_engine = build_rag_engine(query=query, top_k=top_k, file_ids=file_ids, score=score, api_key=api_key,
                                    model=model, instructions=instructions,
                                    metadata_filters=metadata_filters,
                                    top_p=top_p, temperature=temperature, max_tokens=max_tokens, stream=False,
                                    retrieve_mode=retrieve_mode, plugins=plugins, show_quote=show_quote)
    res = query_engine.query(query)
    query_embedding_context.reset(token)
    if isinstance(res, Response):
        return event_handler.convert_query_res_to_rag_response(res.response, res.source_nodes, []).to_dict()
    else:
        text = res.message.content or ""
        return event_handler.convert_query_res_to_rag_response(text, res.source_nodes, res.message.sensitives).to_dict()


def rag_streaming(
        query: str,
        top_k: int = 3,
        file_ids: List[str] = None,
        score: float = 0,
        api_key: str = "",
        model: str = "c4ai-command-r-plus",
        instructions: str = "",
        top_p: int = 1,
        temperature: float = 0.01,
        max_tokens: int = None,
        metadata_filters: MetadataFilters = None,
        retrieve_mode: RetrievalMode = RetrievalMode.SEMANTIC,
        plugins: List[Plugin] = None,
        show_quote: bool = False,
        event_handler: BaseEventHandler = default_event_handler):
    # 初始化流式handler
    streaming_handler = RAGStreamingHandler(event_handler)
    trace_locals = locals().copy()
    # 屏蔽api_key
    trace_locals.pop('api_key', None)
    trace_args = list(trace_locals.values())
    embedding_token = query_embedding_context.set([])
    start = int(time.time() * 1000)

    file_ids = file_service.filter_deleted_files(file_ids)
    query_engine = build_rag_engine(query=query, top_k=top_k, file_ids=file_ids, score=score, api_key=api_key,
                                    model=model, instructions=instructions,
                                    metadata_filters=metadata_filters,
                                    top_p=top_p, temperature=temperature, max_tokens=max_tokens, stream=True,
                                    retrieve_mode=retrieve_mode, plugins=plugins, show_quote=show_quote)

    streaming_response = query_engine.query(query)
    aid = str(uuid.uuid4()) if not TraceContext.trace_id else TraceContext.trace_id
    retrieval_send = False

    llm_response = ""
    user_logger.info(f"rag request id: {TraceContext.trace_id} start receive stream delta")
    error_request = False
    for item in streaming_response.response_gen:
        user_logger.info(f"rag request id: {TraceContext.trace_id} message delta: {item}")
        if not retrieval_send:
            retrieval_send = True
            yield from streaming_handler.create_retrieval_stream(
                id=aid,
                nodes=streaming_response.source_nodes,
                event_type='retrieval.completed',
            )

        if isinstance(item, APIError):
            error_request = True
            trace_handler.log_trace('rag_streaming', TraceContext.trace_id, int(time.time() * 1000) - start, start, '', item,
                      trace_args)
            yield from streaming_handler.create_error_stream(
                id=aid, event_type='error', error=item,
            )
        elif isinstance(item, list) and item and isinstance(item[0], Sensitive):
            # 敏感词事件透传
            yield from streaming_handler.create_sensitive_stream(
                id=aid, sensitives=item, event_type='message.sensitives'
            )
        else:
            llm_response += item
            yield from streaming_handler.create_msg_stream(
                id=aid, value=item, event_type='message.delta'
            )
    msg_complete_event = streaming_handler.create_msg_stream(id=aid, value=llm_response,
                                                             nodes=streaming_response.source_nodes,
                                                             event_type='message.completed')
    if not error_request:
        trace_handler.log_trace('rag_streaming', TraceContext.trace_id, int(time.time() * 1000) - start, start,
                  llm_response, '', trace_args)
        yield from msg_complete_event

    query_embedding_context.reset(embedding_token)


def build_rag_engine(
        query: str,
        # 检索参数
        top_k: int = 3,
        file_ids: List[str] = None,
        score: float = 0,
        # 模型生成参数
        api_key: str = "",
        model: str = "c4ai-command-r-plus",
        instructions: str = "",
        top_p: int = 1,
        temperature: float = 0.01,
        max_tokens: int = None,
        metadata_filters: MetadataFilters = None,
        stream: bool = False,
        retrieve_mode: RetrievalMode = RetrievalMode.SEMANTIC,
        plugins: List[Plugin] = None,
        show_quote: bool = False,
) -> RetrieverQueryEngine:
    user_logger.info(f"rag start, query : {query}, file_ids : {file_ids}, user : {UserContext.user_id}")
    llm = OpenAPI(temperature=temperature, api_base=OPENAPI["URL"], api_key=api_key, timeout=300,
                  system_prompt=instructions, additional_kwargs={"top_p": top_p}, model=model)

    # 构建检索器
    retriever = create_retriever_by_mode(metadata_filters=metadata_filters, score=score, file_ids=file_ids,
                                         retrieve_mode=retrieve_mode, plugins=plugins)

    # 根据提供插件构建后置处理器
    node_postprocessors = get_components_from_plugins(plugins, BaseNodePostprocessor)
    # 添加默认后置处理器
    node_postprocessors.extend(build_postprocessor_from_retrieve_param(score, top_k, retrieve_mode))

    response_synthesizer = get_llm_response_synthesizer(
        llm=llm,
        model=model,
        instruction=instructions,
        max_tokens=max_tokens,
        text_qa_template=get_rag_template(instructions=instructions, plugins=plugins, show_quote=show_quote),
        response_mode=ResponseMode.SIMPLE_SUMMARIZE,
        service_context=None,
        streaming=stream,
        response_generators=[StandardAnswerGenerator(match_score=RETRIEVAL['MATCH_SCORE'])],
        extra_headers=get_extra_headers(model),
        # 限制非流式输出类型
        output_cls=ChatResponse,
    )

    return RetrieverQueryEngine(
        retriever=retriever,
        response_synthesizer=response_synthesizer,
        node_postprocessors=node_postprocessors,
    )


@trace("retrieval")
def retrieval(file_ids: List[str], query: str, top_k: int, score: float, metadata_filters: MetadataFilters,
              retrieve_mode: RetrievalMode = RetrievalMode.SEMANTIC,
              plugins: List[Plugin] = None,
              ) -> List[NodeWithScore]:
    user_logger.info(f"retrieval start, query : {query}, file_ids : {file_ids}, top_k : {top_k}")
    token = query_embedding_context.set([])
    file_ids = file_service.filter_deleted_files(file_ids)
    # 构建多路检索器
    retriever = create_retriever_by_mode(metadata_filters=metadata_filters, score=score, file_ids=file_ids,
                                         retrieve_mode=retrieve_mode, plugins=plugins)

    # 检索
    with callback_manager.as_trace("retrieve"):
        score_nodes = retriever._retrieve(query_bundle=QueryBundle(query_str=query))

    # 根据提供插件构建后置处理器
    node_postprocessors = get_components_from_plugins(plugins, BaseNodePostprocessor)
    # 添加默认后置处理器
    node_postprocessors.extend(build_postprocessor_from_retrieve_param(score, top_k, retrieve_mode))

    for postprocessor in node_postprocessors:
        score_nodes = postprocessor.postprocess_nodes(nodes=score_nodes, query_str=query)

    query_embedding_context.reset(token)
    return score_nodes


def get_extra_headers(model: str) -> Headers:
    if TraceContext.is_mock_request or model == MOCK_MODEL:
        return get_mock_data()
    return None


def get_mock_data() -> Headers:
    def generate_random_string(length: int) -> str:
        letters = string.ascii_letters + string.digits
        return ''.join(random.choice(letters) for _ in range(length))

    ttft = random.randint(100, 3000)
    interval = random.randint(100, 500)
    return {
        # mock数据内容
        "X-BELLA-MOCK-TEXT": str(generate_random_string(random.randint(20, 500))),
        # mock首包响应时长，stream为true时生效
        "X-BELLA-MOCK-TTFT": str(ttft),
        # mock每包间隔时长
        "X-BELLA-MOCK-INTERVAL": str(interval),
        # mock请求的响应时长
        "X-BELLA-MOCK-TTLT": str(random.randint(ttft + interval, ttft + interval + 5000)),
        "X-BELLA-MOCK-REQUEST": 'true'
    }
