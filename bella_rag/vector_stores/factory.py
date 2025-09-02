"""
Index Factory
索引工厂类，支持用户注册自定义的index配置
"""

from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.vector_stores.types import BasePydanticVectorStore

from init.settings import user_logger
from bella_rag.vector_stores.index import BaseIndex
from bella_rag.transformations.index_extend.index_extend_transform_component import IndexExtendTransformComponent

logger = user_logger

@dataclass
class IndexConfig:
    """索引配置"""
    name: str
    vector_store: BasePydanticVectorStore
    embed_model: Optional[BaseEmbedding] = None
    index_structure: Optional[BaseIndex] = None
    index_extend: Optional[IndexExtendTransformComponent] = None
    extra_params: Dict[str, Any] = field(default_factory=dict)
    description: Optional[str] = None


class IndexFactory:
    """索引工厂类"""

    def __init__(self):
        self._indexes: Dict[str, IndexConfig] = {}
        self._index_instances: Dict[str, VectorStoreIndex] = {}
    
    def register_index(
        self,
        name: str,
        vector_store: BasePydanticVectorStore,
        embed_model: Optional[BaseEmbedding] = None,
        index_structure: Optional[BaseIndex] = None,
        index_extend: Optional[IndexExtendTransformComponent] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ) -> 'IndexFactory':
        """
        注册索引配置
        
        Args:
            name: 索引名称
            vector_store: 向量存储实例
            embed_model: 嵌入模型
            index_structure: 索引结构
            index_extend: 索引扩展组件
            extra_params: 额外参数
            description: 描述信息
            
        Returns:
            self: 支持链式调用
        """
        config = IndexConfig(
            name=name,
            vector_store=vector_store,
            embed_model=embed_model,
            index_structure=index_structure,
            index_extend=index_extend,
            extra_params=extra_params or {},
            description=description
        )
        self._indexes[name] = config
        return self
    
    def get_index(self, name: str) -> VectorStoreIndex:
        """获取索引实例"""
        if name not in self._indexes:
            raise ValueError(f"Index '{name}' not registered")
        
        if name not in self._index_instances:
            config = self._indexes[name]
            
            # 构建索引参数
            index_params = {
                'nodes': [],
                'storage_context': StorageContext.from_defaults(vector_store=config.vector_store),
                **config.extra_params
            }
            
            if config.embed_model:
                index_params['embed_model'] = config.embed_model
            
            self._index_instances[name] = VectorStoreIndex(**index_params)
        
        return self._index_instances[name]
    
    def list_indexes(self) -> List[str]:
        """列出所有注册的索引"""
        return list(self._indexes.keys())
    
    def get_index_info(self, name: str) -> Dict[str, Any]:
        """获取索引信息"""
        if name not in self._indexes:
            raise ValueError(f"Index '{name}' not registered")
        
        config = self._indexes[name]
        return {
            'name': config.name,
            'vector_store_type': type(config.vector_store).__name__,
            'description': config.description,
            'has_embed_model': config.embed_model is not None,
            'has_index_structure': config.index_structure is not None,
            'has_index_extend': config.index_extend is not None,
            'extra_params': config.extra_params
        }
    
    def create_from_config(self, config_dict: Dict[str, Any]) -> 'IndexFactory':
        """从配置字典创建索引"""
        for index_name, index_config in config_dict.items():
            self.register_index(
                name=index_name,
                vector_store=index_config['vector_store'],
                embed_model=index_config.get('embed_model'),
                index_structure=index_config.get('index_structure'),
                index_extend=index_config.get('index_extend'),
                extra_params=index_config.get('extra_params', {}),
                description=index_config.get('description')
            )
        return self
    
    def clear(self):
        """清空所有注册的配置和实例"""
        self._indexes.clear()
        self._index_instances.clear()
    
    def has_index(self, name: str) -> bool:
        """检查索引是否已注册"""
        return name in self._indexes
    
    def remove_index(self, name: str) -> bool:
        """移除已注册的索引"""
        if name in self._indexes:
            del self._indexes[name]
            if name in self._index_instances:
                del self._index_instances[name]
            return True
        return False


# 全局工厂实例
index_factory = IndexFactory()


def register_index(
    name: str,
    vector_store: BasePydanticVectorStore,
    embed_model: Optional[BaseEmbedding] = None,
    index_structure: Optional[BaseIndex] = None,
    index_extend: Optional[IndexExtendTransformComponent] = None,
    extra_params: Optional[Dict[str, Any]] = None,
    description: Optional[str] = None
) -> IndexFactory:
    """便捷的注册索引函数"""
    logger.info(f'Registering index {name}, description: {description}')
    return index_factory.register_index(
        name, vector_store, embed_model, index_structure, index_extend, extra_params, description
    )


def get_index(name: str) -> VectorStoreIndex:
    """便捷的获取索引函数"""
    return index_factory.get_index(name)
    
def get_store(name: str) -> BasePydanticVectorStore:
    """便捷的获取向量存储函数"""
    index = get_index(name)
    return index.vector_store if index else None

def has_index(name: str) -> bool:
    """便捷的检查索引函数"""
    return index_factory.has_index(name)


def remove_index(name: str) -> bool:
    """便捷的移除索引函数"""
    return index_factory.remove_index(name) 