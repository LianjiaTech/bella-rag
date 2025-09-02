import textwrap
from abc import abstractmethod
from enum import Enum
from hashlib import sha256
from typing import Dict, Union, List, Optional, Any, Set

from bella_openapi import Cell
from llama_index.core.schema import BaseNode as LlamaBaseNode
from llama_index.core.schema import ImageNode as LlamaImageNode, WRAP_WIDTH
from llama_index.core.schema import NodeWithScore as LlamaNodeWithScore
from llama_index.core.schema import TextNode as LlamaTextNode
from llama_index.core.utils import truncate_text

from bella_rag.meta.meta_data import NodeTypeEnum

TRUNCATE_LENGTH = 2000


class DocumentNodeRelationship(Enum):
    """Node relationships used in `BaseNode` class.

    Attributes:
        SOURCE: The node is the source document.
        PREVIOUS: The node is the previous node in the document.
        NEXT: The node is the next node in the document.
        PARENT: The node is the parent node in the document.
        CHILD: The node is a child node in the document.

        扩展类型：
        LEFT/RIGHT/UP/DOWN
    """
    SOURCE = "source"
    PREVIOUS = "previous"
    NEXT = "next"
    PARENT = "parent"
    CHILD = "child"
    # 存在多个子节点且子节点为链表形式，可用该关系表达
    HEAD_CHILD = "head_child"

    # 扩展节点关系
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"
    # leaf节点关联的上下文节点
    CONTEXTUAL = "contextual"
    # 上下文节点关联的leaf节点组
    CONTEXTUAL_GROUP = "contextual_group"
    # 节点补全的节点组
    COMPLETE_GROUP = "complete_group"

    @staticmethod
    def get_relationship_by_value(value: str):
        return DocumentNodeRelationship._value2member_map_[value]

    @staticmethod
    def is_same_level(value: str) -> bool:
        return DocumentNodeRelationship.PREVIOUS.value == value \
            or DocumentNodeRelationship.NEXT.value == value \
            or DocumentNodeRelationship.LEFT.value == value \
            or DocumentNodeRelationship.RIGHT.value == value \
            or DocumentNodeRelationship.UP.value == value \
            or DocumentNodeRelationship.DOWN.value == value


class MetadataMode(str, Enum):
    ALL = "all"
    EMBED = "embed"
    LLM = "llm"
    RERANK = "rerank"
    NONE = "none"


class BaseNode(LlamaBaseNode):
    pos: int = -911

    @abstractmethod
    def get_complete_content(self, metadata_mode: MetadataMode = MetadataMode.NONE) -> str:
        """
        补全
        """

    @abstractmethod
    def get_node_type(self) -> str:
        """
        返回node_type
        """

    def get_content(self, metadata_mode: MetadataMode = MetadataMode.NONE) -> str:
        if self.text == "":
            return " "
        return self.text

    def set_node_pos(self, pos: int):
        self.pos = pos

    @abstractmethod
    def unique_key(self) -> str:
        """
        获取节点唯一性判断标识
        """

    def __str__(self) -> str:
        """打印节点的complete content"""
        source_text_truncated = truncate_text(
            self.get_complete_content().strip(), TRUNCATE_LENGTH
        )
        source_text_wrapped = textwrap.fill(
            f"Text: {source_text_truncated}\n", width=WRAP_WIDTH
        )
        return f"Node ID: {self.node_id}\n{source_text_wrapped}"


class NodeWithScore(LlamaNodeWithScore):
    node: BaseNode
    similarity_score: Optional[float] = None  # 向量score
    rerank_score: Optional[float] = None  # rerank模型打分
    es_score: Optional[float] = None  # 关键词相关性得分

    pass_rerank: Optional[bool] = False

    @property
    def unique_key(self) -> str:
        return self.node.unique_key()


RelatedNode = Union[BaseNode, List[BaseNode], Set[BaseNode]]


class StructureNode(BaseNode):
    # 当前元素的有序列表序号 1.1, 1.2.1
    order_num_str: Optional[str] = ''
    # 节点及子节点token总数
    token: Optional[int] = -911
    doc_relationships: Optional[Dict[DocumentNodeRelationship, RelatedNode]] = {}
    # 关联的上下文节点id
    context_id: Optional[str] = ''
    is_mock: Optional[bool] = False

    def extend_complete_group_nodes(self, nodes: List[BaseNode]):
        # 使用集合来避免重复检查
        if DocumentNodeRelationship.COMPLETE_GROUP not in self.doc_relationships:
            self.doc_relationships[DocumentNodeRelationship.COMPLETE_GROUP] = set(nodes)
        else:
            existing_nodes = self.doc_relationships[DocumentNodeRelationship.COMPLETE_GROUP]
            existing_nodes.update(nodes)  # 使用集合的 update 方法

    def get_complete_group_nodes(self) -> List[BaseNode]:
        # 使用 get 方法简化逻辑
        return list(self.doc_relationships.get(DocumentNodeRelationship.COMPLETE_GROUP, []))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.id_ == other.id_
        else:
            return False

    def dict(self, **kwargs: Any) -> Dict[str, Any]:
        exclude = kwargs.pop('exclude', set())
        exclude = exclude or set()
        exclude.add("doc_relationships")
        return super().dict(**kwargs, exclude=exclude)

    def hash(self) -> str:
        doc_identity = str(self.text) + str(self.metadata) + str(self.doc_relationships)
        return str(sha256(doc_identity.encode("utf-8", "surrogatepass")).hexdigest())

    def unique_key(self) -> str:
        return str(self.get_node_type()) + '-' + str(self.get_complete_content()) + '-' + str(self.pos)

    def __hash__(self):
        return hash(self.id_)


class TextNode(StructureNode, LlamaTextNode):
    class Config:
        arbitrary_types_allowed = True

    def get_complete_content(self, metadata_mode: MetadataMode = MetadataMode.NONE):
        complete_content = self.text
        # 生成阶段图片补充ocr信息
        if metadata_mode == MetadataMode.RERANK or metadata_mode == MetadataMode.LLM:
            complete_group_nodes = self.get_complete_group_nodes()
            for group_node in complete_group_nodes:
                if isinstance(group_node, ImageNode) and group_node.image_url in complete_content:
                    complete_content = complete_content.replace(group_node.image_url,
                                                                group_node.get_complete_content(metadata_mode))
        return complete_content

    def get_node_type(self) -> str:
        return NodeTypeEnum.TEXT.node_type_code


class TabelNode(TextNode):
    # 表格节点元信息
    cell: Optional[Cell] = None

    def dict(self, **kwargs: Any) -> Dict[str, Any]:
        exclude = kwargs.pop('exclude', set())
        exclude = exclude or set()
        exclude.add("cell")
        return super().dict(**kwargs, exclude=exclude)


class ImageNode(StructureNode, LlamaImageNode):
    """
    图像节点使用ocr结果建索引，使用图片链接作为检索展示结果
    """
    image_ocr_result: Optional[str] = ''

    def get_complete_content(self, metadata_mode: MetadataMode = MetadataMode.NONE) -> str:
        if self.image_ocr_result:
            if metadata_mode == MetadataMode.RERANK:
                # rerank使用ocr结果
                return self.image_ocr_result
            elif metadata_mode == MetadataMode.LLM:
                # 生成使用ocr结果 + 图片url模板化
                return (f'\n[图片信息]\n'
                        f'图片链接：{self.image_url}\n'
                        f'图片视觉信息：{self.image_ocr_result}\n')
        return self.image_url or ""

    def get_content(self, metadata_mode: MetadataMode = MetadataMode.NONE) -> str:
        return self.image_ocr_result or " "

    def get_node_type(self) -> str:
        return NodeTypeEnum.IMAGE.node_type_code

    def set_content(self, value: str) -> None:
        url = "" if not value else value
        self.image_url = url
        self.text = url


class QaNode(BaseNode, LlamaTextNode):
    question_str: Optional[str]
    answer_str: Optional[str]
    group_id: Optional[str]

    # 业务自定义字段，bella-rag只负责存储，不负责检索，是个通用能力字段
    business_metadata: Optional[str]

    def get_content(self, metadata_mode: MetadataMode = MetadataMode.NONE) -> str:
        return self.question_str

    def set_qa(self, question: str, answer: str) -> None:
        self.question_str = question
        self.answer_str = answer

    def get_complete_content(self, metadata_mode: MetadataMode = MetadataMode.NONE):
        return "【问题】{} \n【答案】{}".format(self.question_str, self.answer_str)

    def get_node_type(self) -> str:
        return NodeTypeEnum.QA.node_type_code

    def hash(self) -> str:
        doc_identity = str(self.question_str) + str(self.answer_str) + str(self.metadata)
        return str(sha256(doc_identity.encode("utf-8", "surrogatepass")).hexdigest())

    def unique_key(self) -> str:
        return str(self.get_node_type()) + '-' + str(self.get_complete_content())


def is_contextual_node(node: BaseNode) -> bool:
    """
    判断节点为上下文节点：包含CONTEXTUAL_GROUP关系
    """
    return isinstance(node, StructureNode) and node.doc_relationships \
        and DocumentNodeRelationship.CONTEXTUAL_GROUP in node.doc_relationships.keys()
