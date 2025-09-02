from abc import abstractmethod
from typing import List, Any

from llama_index.core.schema import TransformComponent, BaseNode


class IndexExtendTransformComponent(TransformComponent):
    """
    因为可能数据安全问题腾讯向量库存放公司数据可能有泄露风险，业务放可以继承此类自定义实现内容存储，也可以直接存索引内，但需要谨慎
    """
    def __call__(self, nodes: List["BaseNode"], **kwargs: Any) -> List["BaseNode"]:
        self.build_recall_index(nodes)
        return nodes

    @abstractmethod
    def build_recall_index(self, nodes: List[BaseNode]):
        """Transform nodes."""

    @abstractmethod
    def set_node_content(self, node: BaseNode):
        """Set content from nodes."""

    @abstractmethod
    def batch_set_node_contents(self, nodes: List[BaseNode]):
        """batch set content from nodes"""

    @abstractmethod
    async def async_batch_set_node_contents(self, nodes: List[BaseNode]):
        """async batch set content from nodes"""

    @abstractmethod
    def support_node_type(self):
        """获取支持插入的节点类型"""
