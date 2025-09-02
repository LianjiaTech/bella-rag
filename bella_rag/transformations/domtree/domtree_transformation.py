from typing import List, Any

from llama_index.core.schema import BaseNode, TransformComponent

from bella_rag.transformations.util.decorator import parser_decorator
from bella_rag.utils.file_api_tool import file_api_client
from bella_rag.utils.schema_util import dom2nodes
from bella_rag.utils.trace_log_util import trace

SUPPORTED_FILE_TYPES = ["pdf", "doc", "docx", "xlsx", "xls"]


class DomTreeParser(TransformComponent):
    """
    DomTree处理的Transformation组件
    
    直接从Document中提取file_id，调用file API获取domtree并转换为BaseNode列表
    """

    @trace("domtree_parse")
    @parser_decorator
    def __call__(
            self,
            nodes: List[BaseNode],
            show_progress: bool = False,
            **kwargs: Any
    ) -> List[BaseNode]:
        """
        对nodes进行domtree转换
        
        Args:
            nodes: 输入的节点列表（通常来自DomTreeDocumentReader）
            show_progress: 是否显示进度
            **kwargs: 其他参数
            
        Returns:
            List[BaseNode]: domtree转换后的节点列表
        """
        if not nodes:
            return []

        file_id = nodes[0].node_id
        dom = file_api_client.parse_pdf_from_json(file_id)
        return dom2nodes(dom)

    @classmethod
    def supports_file_type(cls, file_type: str) -> bool:
        """
        检查是否支持指定的文件类型
        
        Args:
            file_type: 文件类型
            
        Returns:
            bool: 是否支持
        """
        return file_type in SUPPORTED_FILE_TYPES
