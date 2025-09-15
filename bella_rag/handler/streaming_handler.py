import json
from abc import ABC, abstractmethod
from typing import List, Generator, Any

from openai import APIError

from app.response.entity import ChatFileCitation, Text as RagText, Annotation as RagAnnotation, \
    Content as RagContent, Message
from app.response.rag_response import RagStreamSensitive
from app.services import chunk_vector_index_structure
from app.utils.convert import convert_score_nodes_to_search_res, parse_paths_from_node
from bella_rag.llm.types import Sensitive
from bella_rag.schema.nodes import NodeWithScore


class BaseEventHandler(ABC):

    def yield_event(self, event: str, data: Any) -> Generator[str, None, None]:
        """通用事件生成方法"""
        yield f"event: {event}\n"
        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    @abstractmethod
    def generate_message_stream(self, id: str, event_type: str, value: str = None,
                                nodes: List[NodeWithScore] = None) -> Generator[str, None, None]:
        """生成消息事件流"""
        pass

    @abstractmethod
    def generate_retrieval_stream(self, id: str, event_type: str,
                                  nodes: List[NodeWithScore] = None) -> Generator[str, None, None]:
        """生成检索事件流"""
        pass

    @abstractmethod
    def generate_sensitive_stream(self, id: str, event_type: str,
                                  sensitives: List[Sensitive] = None) -> Generator[str, None, None]:
        """生成敏感词事件流"""
        pass

    @abstractmethod
    def generate_error_stream(self, id: str, event_type: str, error: APIError) -> Generator[str, None, None]:
        """生成error事件流"""
        pass

    @abstractmethod
    def convert_query_res_to_rag_response(self, text: str, score_nodes: List[NodeWithScore],
                                          sensitives: List[Sensitive]):
        """rag query输出协议转换"""
        pass


class RagEventHandler(BaseEventHandler):

    def generate_message_stream(self, id: str, event_type: str, value: str = None,
                                nodes: List[NodeWithScore] = None) -> Generator[str, None, None]:
        if event_type == "message.delta":
            text = RagText(value=value, annotations=[])
            content = RagContent(type='text', text=[text])
            data = {
                'id': id,
                'object': 'message.delta',
                'delta': Message(content=[content]).to_dict()
            }
            yield from self.yield_event(event_type, data)
        else:
            yield

    def generate_retrieval_stream(self, id: str, event_type: str,
                                  nodes: List[NodeWithScore] = None) -> Generator[str, None, None]:
        docs = []
        if nodes:
            search_res = convert_score_nodes_to_search_res(nodes)
            docs = search_res.docs

        data = {
            'id': id,
            'object': 'retrieval.doc',
            'doc': [d.to_dict() for d in docs]
        }
        yield from self.yield_event(event_type, data)

    def generate_sensitive_stream(self, id: str, event_type: str,
                                  sensitives: List[Sensitive] = None) -> Generator[str, None, None]:
        data = RagStreamSensitive(
            sensitives=sensitives,
            id=id,
            object='message.sensitives'
        ).json_response()
        yield from self.yield_event(event_type, data)

    def generate_error_stream(self, id: str, event_type: str, error: APIError) -> Generator[str, None, None]:
        yield from self.yield_event(event_type, error.body)

    def convert_query_res_to_rag_response(self, text: str, score_nodes: List[NodeWithScore],
                                          sensitives: List[Sensitive]):
        annotations = []
        for score_node in score_nodes:
            annotations.append(RagAnnotation(type='file_citation',
                                             file_citation=ChatFileCitation(
                                                 file_id=score_node.metadata[chunk_vector_index_structure.doc_id_key],
                                                 file_name=score_node.metadata[chunk_vector_index_structure.doc_name_key],
                                                 paths=parse_paths_from_node(score_node.node)
                                             )))
        rag_text = RagText(value=text, annotations=annotations)
        content = RagContent(type='text', sensitives=sensitives, text=[rag_text])
        return Message(content=[content])


class RAGStreamingHandler:
    def __init__(self, event_handler: BaseEventHandler):
        self.event_handler = event_handler

    def create_msg_stream(self, id: str, event_type: str, **kwargs) -> Generator:
        return self.event_handler.generate_message_stream(
            id=id,
            event_type=event_type,
            **kwargs
        )

    def create_retrieval_stream(self, id: str, event_type: str, **kwargs) -> Generator:
        return self.event_handler.generate_retrieval_stream(
            id=id,
            event_type=event_type,
            **kwargs
        )

    def create_sensitive_stream(self, id: str, event_type: str, **kwargs) -> Generator:
        return self.event_handler.generate_sensitive_stream(
            id=id,
            event_type=event_type,
            **kwargs
        )

    def create_error_stream(self, id: str, event_type: str, **kwargs) -> Generator:
        return self.event_handler.generate_error_stream(
            id=id,
            event_type=event_type,
            **kwargs
        )

    def create_done(self):
        return self.event_handler.yield_event("done", "[DONE]")
