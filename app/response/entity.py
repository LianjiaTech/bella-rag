from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from bella_rag.llm.types import Sensitive


@dataclass
class RagSearchAnnotation:
    """注解类 - 文件的元信息"""
    file_id: str
    file_name: Optional[str] = None
    paths: Optional[List[List]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'file_id': self.file_id,
            'file_name': self.file_name,
            'paths': self.paths
        }
        return result


@dataclass
class RagSearchDoc:
    """rag检索条目"""
    type: str
    text: str   # todo 当前是文本，后续可支持domtree，markdown等
    annotation: RagSearchAnnotation
    score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            'type': self.type,
            'text': self.text,
            'annotation': self.annotation.to_dict()
        }
        if self.score is not None:
            result['score'] = self.score
        return result


@dataclass
class RagSearchData:
    """检索数据，包括分页参数等"""
    docs: List[RagSearchDoc]
    total: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        result['docs'] = [doc.to_dict() for doc in self.docs]
        if self.total is not None:
            result['total'] = int(self.total)
        return result


@dataclass  
class ChatFileCitation:
    """专门用于chat接口的文件引用类"""
    file_id: str
    file_name: Optional[str] = None
    path: Optional[List[int]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'file_id': self.file_id,
            'file_name': self.file_name,
            'path': self.path  # chat接口返回path字段
        }

@dataclass
class Annotation:
    type: str
    file_citation: ChatFileCitation

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type,
            'file_citation': self.file_citation.to_dict()
        }


@dataclass
class Text:
    value: str
    annotations: List[Annotation]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'value': self.value,
            'annotations': [ann.to_dict() for ann in self.annotations]
        }


@dataclass
class Content:
    type: str
    text: List[Text]
    sensitives: Optional[List[Sensitive]] = None

    def to_dict(self) -> Dict[str, Any]:
        res = {
            'type': self.type,
            'text': [t.to_dict() for t in self.text]
        }
        if self.sensitives:
            res['sensitives'] = [s.to_dict() for s in self.sensitives]
        return res


@dataclass
class Message:
    """rag消息响应体"""
    content: List[Content]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'content': [c.to_dict() for c in self.content]
        }
