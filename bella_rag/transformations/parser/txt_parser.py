from typing import Any, Sequence, List

from llama_index.core.node_parser import TokenTextSplitter
from llama_index.core.schema import BaseNode, MetadataMode

from bella_rag.schema.nodes import TextNode
from bella_rag.transformations.util.decorator import parser_decorator
from bella_rag.utils.trace_log_util import trace


class TxtParser(TokenTextSplitter):

    def __init__(self, chunk_size=500, chunk_overlap=100):
        super().__init__(chunk_size, chunk_overlap)

    @parser_decorator
    @trace("txt_parse")
    def _parse_nodes(
            self,
            nodes: Sequence[BaseNode],
            show_progress: bool = False,
            **kwargs: Any,
    ) -> List[BaseNode]:
        supper_result: List[BaseNode] = super()._parse_nodes(nodes=nodes, show_progress=show_progress, **kwargs)
        result: List[TextNode] = [TextNode(text=node.get_content(metadata_mode=MetadataMode.NONE))
                                  for node in supper_result]
        return result
