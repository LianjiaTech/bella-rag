from dataclasses import dataclass
from typing import Dict, Any, List

from llama_index.core.base.llms.types import ChatResponse as LlamaChatResponse, ChatMessage as LlamaChatMessage


class RankItem:
    document: Dict[str, Any]
    index: int
    relevance_score: float


class RerankResponse:
    id: str
    meta: Dict[str, Any]
    results: List[RankItem]
    model: str

    def __init__(self, id: str, meta: Dict[str, Any], results: List[RankItem], model: str):
        self.id = id
        self.meta = meta
        self.results = results
        self.model = model
        self.model = model


@dataclass
class SensitiveDetail:
    offset: int
    length: str
    word: str

    def json_response(self):
        return {
            'offset': self.offset,
            'length': self.length,
            'word': self.word,
        }

    def to_dict(self) :
        return self.json_response()

@dataclass
class Sensitive:
    count: int
    detail: List[SensitiveDetail]
    type: str

    def json_response(self):
        return {
            'count': self.count,
            'type': self.type,
            'detail': [
                d.json_response()
                for d in self.detail
            ]
        }

    def to_dict(self) :
        return self.json_response()


def dict_to_sensitive(data: dict) -> Sensitive:
    details = [
        SensitiveDetail(
            offset=detail['offset'],
            length=detail['length'],
            word=detail['word']
        ) for detail in data.get('detail', [])
    ]
    return Sensitive(
        count=data['count'],
        detail=details,
        type=data['type']
    )


class ChatMessage(LlamaChatMessage):
    sensitives: List[Sensitive] = []


class ChatResponse(LlamaChatResponse):
    message: ChatMessage
