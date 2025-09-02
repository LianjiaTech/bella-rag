from abc import ABC, abstractmethod
from typing import List

from llama_index.core.base.response.schema import RESPONSE_TYPE, Response
from llama_index.core.schema import BaseComponent

from bella_rag.schema.nodes import QaNode, NodeWithScore
from bella_rag.utils.trace_log_util import trace


class CustomGenerator(BaseComponent, ABC):
    class Config:
        arbitrary_types_allowed = True

    def response_generate(
        self,
        nodes: List[NodeWithScore],
    ) -> RESPONSE_TYPE:
        """Preprocess nodes."""
        return self._response_generate(nodes)

    @abstractmethod
    def _response_generate(
        self,
        nodes: List[NodeWithScore],
    ) -> RESPONSE_TYPE:
        """Preprocess nodes."""


class StandardAnswerGenerator(CustomGenerator):

    match_score: float = 0.95

    class Config:
        arbitrary_types_allowed = True

    @trace("standard_answer_generator")
    def _response_generate(
        self,
        nodes: List[NodeWithScore],
    ) -> RESPONSE_TYPE:
        """Preprocess nodes."""
        for node in nodes:
            if isinstance(node.node, QaNode) and node.similarity_score and node.similarity_score > self.match_score:
                return Response(
                    response=node.node.answer_str,
                    source_nodes=[node]
                )

        return None
