from typing import Sequence, Any, List, Dict

from llama_index.core.node_parser import NodeParser
from llama_index.core.schema import BaseNode, Document


class DocParser(NodeParser):

    def _parse_nodes(
            self,
            nodes: Sequence[BaseNode],
            show_progress: bool = False,
            **kwargs: Any,
    ) -> List[BaseNode]:
        pass

    def _postprocess_parsed_nodes(
            self, nodes: List[BaseNode], parent_doc_map: Dict[str, Document]
    ) -> List[BaseNode]:
        pass


class DocxParser(NodeParser):

    def _parse_nodes(
            self,
            nodes: Sequence[BaseNode],
            show_progress: bool = False,
            **kwargs: Any,
    ) -> List[BaseNode]:
        pass

    def _postprocess_parsed_nodes(
            self, nodes: List[BaseNode], parent_doc_map: Dict[str, Document]
    ) -> List[BaseNode]:
        pass
