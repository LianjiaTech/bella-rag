from typing import Any, Sequence, List

from llama_index.core.node_parser import TokenTextSplitter
from llama_index.core.schema import BaseNode, MetadataMode

from bella_rag.schema.nodes import TextNode
from bella_rag.transformations.util.decorator import parser_decorator
from bella_rag.utils.trace_log_util import trace


class PdfParser(TokenTextSplitter):
    """
    基于框架TokenTextSplitter的PDF解析器
    
    简易pdf解析器，使用size + overlap拆分pdf文本
    推荐使用更优的domtree解析方式
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        super().__init__(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    @parser_decorator
    @trace("pdf_parse")
    def _parse_nodes(
            self,
            nodes: Sequence[BaseNode],
            show_progress: bool = False,
            **kwargs: Any,
    ) -> List[BaseNode]:
        # 使用父类的分割逻辑
        super_result: List[BaseNode] = super()._parse_nodes(nodes=nodes, show_progress=show_progress, **kwargs)

        # 转换为TextNode并添加PDF特定的metadata
        result: List[TextNode] = []
        for i, node in enumerate(super_result):
            text_node = TextNode(
                text=node.get_content(metadata_mode=MetadataMode.NONE),
                metadata={
                    'source_type': 'pdf',
                    'chunk_index': i,
                    **getattr(node, 'metadata', {})
                }
            )
            result.append(text_node)

        return result
