from typing import Sequence, Any, List

import pandas as pd
from llama_index.core.node_parser import NodeParser

from bella_rag.schema.nodes import BaseNode, TabelNode
from bella_rag.transformations.util.decorator import parser_decorator
from bella_rag.utils.schema_util import build_table_relationships
from bella_rag.utils.trace_log_util import trace


class ExcelParser(NodeParser):

    @parser_decorator
    @trace("excel_parse")
    def _parse_nodes(
            self,
            nodes: Sequence[BaseNode],
            show_progress: bool = False,
            **kwargs: Any,
    ) -> List[BaseNode]:
        all_nodes: List[BaseNode] = []
        sheets = []
        for node in nodes:
            sheets.append(node.sheet)

        sheet_order = 1
        for sheet in sheets:
            df = sheet[1]
            df = df.dropna(how='all').reset_index(drop=True)
            df = df.fillna('')
            # 构建表格单元格二维矩阵
            matrix = [[] for _ in range(df.shape[0] + 1)]
            for i in range(df.shape[1]):
                table_node = TabelNode(
                    text=str(df.columns[i]),
                    order_num_str=self.format_table_order(sheet_order, 1, i + 1),
                )
                matrix[0].insert(i, table_node)
                all_nodes.append(table_node)
            for row_idx, row in df.iterrows():
                for col_idx, val in enumerate(row):
                    table_node = TabelNode(
                        text=str(val),
                        order_num_str=self.format_table_order(sheet_order, row_idx + 1, col_idx + 1),
                    )
                    matrix[row_idx + 1].insert(col_idx, table_node)
                    all_nodes.append(table_node)
            # 构建表格单元格间关系
            build_table_relationships(matrix)
            sheet_order += 1

        return all_nodes

    def format_table_order(self, level: int, row_idx: int, col_idx: int) -> str:
        return f"{level}.{row_idx}-{row_idx}-{col_idx}-{col_idx}"
