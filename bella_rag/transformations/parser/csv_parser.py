import uuid
from typing import Sequence, Any, List

from llama_index.core.node_parser import NodeParser
from llama_index.core.schema import BaseNode
from llama_index.core.utils import get_tqdm_iterable
from demjson3 import decode

from bella_rag.schema.document import CSVDocument
from bella_rag.schema.nodes import QaNode
from bella_rag.transformations.util.decorator import parser_decorator
from bella_rag.utils.trace_log_util import trace


class CsvParser(NodeParser):

    @parser_decorator
    @trace("csv_parse")
    def _parse_nodes(
            self,
            nodes: Sequence[BaseNode],
            show_progress: bool = False,
            **kwargs: Any,
    ) -> List[BaseNode]:
        all_nodes: List[BaseNode] = []
        nodes_with_progress = get_tqdm_iterable(nodes, show_progress, "Parsing nodes")
        for node in nodes_with_progress:
            nodes = self._get_nodes_from_sheet(node)
            all_nodes.extend(nodes)
        return all_nodes

    def _get_nodes_from_sheet(self, node: BaseNode) -> List[BaseNode]:
        """Get nodes from document."""
        if isinstance(node, CSVDocument):
            document: CSVDocument = node
            result: List[BaseNode] = []
            row_id = str(uuid.uuid4())
            for index, item in enumerate(document.sheet):
                similar_questions = item.get('similarQuestions')
                similar_questions = decode(similar_questions.strip().replace('\n', '\\n')) if similar_questions else None
                group_id = row_id + "_" + str(index)
                answer = str(item['answer'])
                general_qa_node = QaNode(question_str=str(item["question"]),
                                         answer_str=answer,
                                         group_id=group_id,
                                         metadata={},)
                result.append(general_qa_node)

                # 相似问解析
                if similar_questions:
                    for similar_question in similar_questions:
                        result.append(QaNode(question_str=similar_question,
                                             answer_str=answer,
                                             group_id=group_id,
                                             metadata={},))

            return result
        else:
            raise TypeError("非csv类型Document")
