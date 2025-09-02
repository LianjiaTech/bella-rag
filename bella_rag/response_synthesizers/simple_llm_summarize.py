from typing import List, Optional, Sequence, Any, cast, Generator

from llama_index.core.base.response.schema import RESPONSE_TYPE, StreamingResponse, Response
from llama_index.core.bridge.pydantic import BaseModel
from llama_index.core.callbacks import CBEventType, EventPayload
from llama_index.core.instrumentation.events.synthesis import SynthesizeStartEvent, SynthesizeEndEvent
from llama_index.core.response_synthesizers import SimpleSummarize
from llama_index.core.response_synthesizers.base import QueryTextType, dispatcher
from llama_index.core.schema import QueryBundle, MetadataMode
from llama_index.core.types import RESPONSE_TEXT_TYPE
from openai._types import Headers

from bella_rag.llm.types import ChatResponse
from bella_rag.preprocessor.ProcessorGenerators import CustomGenerator
from bella_rag.schema.nodes import NodeWithScore
from bella_rag.utils.openapi_util import openapi_modelname_to_contextsize


class SimpleLLMSummarize(SimpleSummarize):
    model: str
    instruction: str
    max_tokens: int
    response_generators: Optional[List[CustomGenerator]] = None
    extra_headers: Optional[Headers] = None

    def __init__(self, model: str, instruction: str, max_tokens: int,
                 response_generators: Optional[List[CustomGenerator]] = None,
                 extra_headers: Optional[Headers] = None,
                 output_cls: Optional[BaseModel] = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.model = model
        self.instruction = instruction
        self.max_tokens = max_tokens
        self.response_generators = response_generators
        self.extra_headers = extra_headers
        self._output_cls = output_cls

    # 去除无score node下的空回复
    @dispatcher.span
    def synthesize(
            self,
            query: QueryTextType,
            nodes: List[NodeWithScore],
            additional_source_nodes: Optional[Sequence[NodeWithScore]] = None,
            **response_kwargs: Any,
    ) -> RESPONSE_TYPE:

        dispatcher.event(
            SynthesizeStartEvent(
                query=query,
            )
        )

        if isinstance(query, str):
            query = QueryBundle(query_str=query)

        with self._callback_manager.event(
                CBEventType.SYNTHESIZE,
                payload={EventPayload.QUERY_STR: query.query_str},
        ) as event:
            response = self.custom_generate(nodes)
            if not response:
                response = self.generate(query=query, nodes=nodes, additional_source_nodes=additional_source_nodes,
                                         **response_kwargs)
            event.on_end(payload={EventPayload.RESPONSE: response})

        dispatcher.event(
            SynthesizeEndEvent(
                query=query,
                response=response,
            )
        )
        return response

    def custom_generate(self, nodes: List[NodeWithScore]) -> RESPONSE_TYPE:
        if not self.response_generators:
            return None
        for generator in self.response_generators:
            response = generator.response_generate(nodes=nodes)
        if response:
            if not self._streaming:
                return response or "Empty Response"
            else:
                return StreamingResponse(response_gen=response_generator(response),
                                         source_nodes=response.source_nodes)

    def generate(self,
                 query: QueryTextType,
                 nodes: List[NodeWithScore],
                 additional_source_nodes: Optional[Sequence[NodeWithScore]] = None,
                 **response_kwargs: Any,
                 ) -> RESPONSE_TYPE:
        text_chunks = [node.node.get_complete_content(metadata_mode=MetadataMode.LLM) for node in nodes]
        response_str = self.get_response(
            query_str=query.query_str,
            text_chunks=text_chunks,
            **response_kwargs,
        )

        additional_source_nodes = additional_source_nodes or []
        source_nodes = list(nodes) + list(additional_source_nodes)

        return self._prepare_response_output(response_str, source_nodes)

    def get_response(
            self,
            query_str: str,
            text_chunks: Sequence[str],
            **kwargs: Any,
    ) -> RESPONSE_TEXT_TYPE:
        single_text_chunk = ''
        for i, text_chunk in enumerate(text_chunks):
            single_text_chunk = single_text_chunk + f'参考信息{i}：\n' + text_chunk + '\n'
        # 检索结果拼接至模板
        text_qa_template = self._text_qa_template.partial_format(recallInfo=single_text_chunk)
        response: RESPONSE_TEXT_TYPE
        if not self._streaming:
            messages = self._llm._get_messages(text_qa_template, query_str=query_str, **kwargs)
            response = self._llm.chat(
                messages,
                model=self.model,
                max_tokens=compute_max_tokens(self.model, self.max_tokens),
                extra_headers=self.extra_headers,
            )
        else:
            response = self._llm.stream(
                text_qa_template,
                query_str=query_str,
                model=self.model,
                max_tokens=compute_max_tokens(self.model, self.max_tokens),
                extra_headers=self.extra_headers,
                **kwargs,
            )

        if isinstance(response, str):
            response = response or "Empty Response"
        elif not isinstance(response, ChatResponse):
            response = cast(Generator, response)

        return response


def response_generator(response: Response):
    yield response.response


def compute_max_tokens(model: str, max_tokens: int) -> Optional[int]:
    if not max_tokens:
        return None
    return min(max_tokens, openapi_modelname_to_contextsize(model))
