from abc import ABC, abstractmethod
from typing import Any, List, Optional

from bella_rag.schema.nodes import BaseNode
from bella_rag.transformations.index_extend.index_extend_transform_component import IndexExtendTransformComponent
from bella_rag.vector_stores.index import VectorIndex
from bella_rag.vector_stores.types import MetadataFilters


class BellaVectorStore(ABC):
    """
    向量存储扩展接口
    
    定义了LlamaIndex原生接口之外的扩展方法
    - 条件更新向量和元数据
    - 条件删除向量
    - 条件查询向量
    - 文档到节点的转换
    """

    @abstractmethod
    def update_vector(
            self,
            metadata_filters: MetadataFilters,
            document: Any
    ) -> None:
        """
        根据元数据过滤器更新向量
        
        Args:
            metadata_filters: 元数据过滤器，用于指定要更新的向量
            document: 要更新的文档数据
        """
        pass

    @abstractmethod
    def update_field_by_filter(
            self,
            filter_key: str,
            filter_value: str,
            field_name: str,
            field_value: str
    ) -> None:
        """
        根据过滤条件更新指定字段
        
        Args:
            filter_key: 过滤字段名
            filter_value: 过滤字段值
            field_name: 要更新的字段名
            field_value: 要更新的字段值
        """
        pass

    @abstractmethod
    def delete_by_filter(self, metadata_filters: MetadataFilters) -> None:
        """
        通过元数据过滤器删除向量
        
        Args:
            metadata_filters: 元数据过滤器，用于指定要删除的向量
        """
        pass

    @abstractmethod
    def query_by_filter(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            document_ids: Optional[List] = None,
            filter_condition: Optional[Any] = None,
            index: Optional[VectorIndex] = None,
            index_extend: Optional[IndexExtendTransformComponent] = None,
            **kwargs: Any
    ) -> List[BaseNode]:
        """
        通过过滤器查询向量
        
        Args:
            limit: 限制返回结果数量
            offset: 偏移量，用于分页
            document_ids: 指定文档ID列表
            filter_condition: 过滤条件，支持MetadataFilters或原生filter类型
            index: 向量索引配置
            index_extend: 索引扩展组件
            **kwargs: 其他查询参数
            
        Returns:
            List[BaseNode]: 查询到的节点列表
        """
        pass

    @abstractmethod
    def doc2node(
            self,
            doc: Any,
            index: Optional[VectorIndex] = None
    ) -> BaseNode:
        """
        将文档转换为节点
        
        Args:
            doc: 向量数据库返回的文档对象
            index: 向量索引配置
            
        Returns:
            BaseNode: 转换后的节点对象
        """
        pass
