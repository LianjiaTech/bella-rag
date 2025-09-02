from typing import Sequence, Any, List, Dict

from bs4 import BeautifulSoup
from llama_index.core.node_parser import NodeParser
from llama_index.core.schema import BaseNode, Document

from bella_rag.schema.nodes import TextNode
from bella_rag.transformations.util.decorator import parser_decorator
from bella_rag.utils.trace_log_util import trace


class HtmlParser(NodeParser):

    @parser_decorator
    @trace("html_parse")
    def _parse_nodes(
            self,
            nodes: Sequence[BaseNode],
            show_progress: bool = False,
            **kwargs: Any,
    ) -> List[BaseNode]:
        html_nodes = []
        for node in nodes:
            soup = BeautifulSoup(node.get_content(), 'html.parser')
            # 表格内容切片
            html_nodes.extend(self.chunk_table_content(soup=soup))
            # 段落内容切片
            html_nodes.extend(self.chunk_paragraphs_content(soup=BeautifulSoup(self.format_html_content(node.get_content()), 'html.parser')))

        return html_nodes

    def chunk_table_content(self, soup: BeautifulSoup) -> List[BaseNode]:
        nodes = []
        tables = soup.select("table")
        for table in tables:
            if table.get_text() and table.get_text().strip():
                lines = table.select("tr")
                for line in lines:
                    # 防止table单格内容超长
                    nodes.append(TextNode(text=line.text))
        return nodes

    def chunk_paragraphs_content(self, soup: BeautifulSoup) -> List[BaseNode]:
        nodes = []
        paragraphs = soup.select("p")
        # 遍历每个段落标签并输出内容
        for paragraph in paragraphs:
            if paragraph.get_text():
                nodes.append(TextNode(text=paragraph.get_text()))
        return nodes

    def format_html_content(self, content: str):
        return (content
                .replace("</ul><p>", ",")
                .replace("</li><p>", ",")
                .replace("</p><li>", ",")
                .replace("</p><ul>", ",")
                .replace("<li>", ",")
                .replace("</li>", ",")
                .replace("<ul>", ",")
                .replace("</ul>", ",")
                .replace("</p><p>", ",")
                .replace("</h1>", ",")
                .replace("<h1>", ",")
                .replace("</h2>", ",")
                .replace("<h2>", ",")
                .replace("</h3>", ",")
                .replace("<h3>", ",")
                .replace("</h4>", ",")
                .replace("<h4>", ",")
                )

    def _postprocess_parsed_nodes(
            self, nodes: List[BaseNode], parent_doc_map: Dict[str, Document]
    ) -> List[BaseNode]:
        return nodes
