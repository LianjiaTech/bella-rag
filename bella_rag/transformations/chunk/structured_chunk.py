import json
from abc import ABC
from typing import Sequence, List, Any

from llama_index.core.schema import BaseNode, TransformComponent

# 基于结构化解析后结果的切片器
class StructuredChunk(TransformComponent, ABC):

    def _parse_nodes(
            self,
            nodes: Sequence[BaseNode],
    ) -> List[BaseNode]:
        # 基于文档结构组织切片，暂时什么都没做
        return nodes

    def chunk_nodes(self, nodes: List[BaseNode], **kwargs: Any) -> List[BaseNode]:
        return self._parse_nodes(nodes, **kwargs)

    async def achunk_nodes(self, nodes: List[BaseNode], **kwargs: Any) -> List[BaseNode]:
        return await self._parse_nodes(nodes, **kwargs)

    def __call__(self, nodes: List[BaseNode], **kwargs: Any) -> List[BaseNode]:
        return self.chunk_nodes(nodes, **kwargs)

    async def acall(self, nodes: List[BaseNode], **kwargs: Any) -> List[BaseNode]:
        return await self.achunk_nodes(nodes, **kwargs)
