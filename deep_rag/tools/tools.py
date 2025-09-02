from abc import abstractmethod
from typing import Any, List, Dict

from app.common.contexts import OpenapiContext
from app.plugin.plugins import Plugin, Completer
from app.services import chunk_vector_index_structure
from app.strategy.retrieval import RetrievalMode
from deep_rag.common.contexts import DeepRagContext
from deep_rag.prompt.tool import compress_prompt, check_read_info_prompt
from init.settings import user_logger, OPENAPI
from bella_rag.llm.openapi import OpenAPI
from bella_rag.utils.complete_util import Small2BigModes

logger = user_logger


class ITool:
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """工具执行"""

    @abstractmethod
    def tool_name(self) -> str:
        """工具名"""


class FileSearchTool(ITool):
    # 检索参数
    plugins: List[Plugin] = [Completer(parameters={"complete_max_length": 1500,
                                                   "complete_mode": Small2BigModes.CONTEXT_COMPLETE.value})]
    top_k: int = 20
    score: float = 0.1
    compress_result: bool = False

    def execute(self, question: str, file_ids: List[str] = [], **kwargs) -> Any:
        logger.info(f"[FileSearchTool] execute. question: {question}, file_ids: {file_ids}")
        from app.services.rag_service import retrieval
        # 使用原始query进行检索
        metadata_filters = kwargs.get("metadata_filters", None)
        retrieve_mode = kwargs.get("retrieve_mode", RetrievalMode.FUSION)
        plugins = kwargs.get("plugins", self.plugins)
        retrieve_res = retrieval(file_ids, DeepRagContext.query, self.top_k, self.score, metadata_filters,
                                 retrieve_mode=retrieve_mode, plugins=plugins)

        search_res = {}
        file_info = {}
        # 按file文件聚合检索结果
        for item in retrieve_res:
            file_id = item.metadata[chunk_vector_index_structure.doc_id_key]
            file_name = item.metadata[chunk_vector_index_structure.doc_name_key]
            content = item.node.get_complete_content()

            if file_id not in search_res:
                search_res[file_id] = []

            search_res[file_id].append(content)
            file_info.update({file_id: file_name})

        res = []
        for k, v in search_res.items():
            res.append({"file_id": k,
                        "file_name": file_info[k],
                        'file_contents': v})

        return self._process_search_contents(DeepRagContext.query, res)

    def _process_search_contents(self, query: str, search_res: List[Dict[str, Any]]):
        if self.compress_result:
            # 进行内容压缩，有效降低模型多轮问答下的噪声
            return self._compress_contents(query, search_res)
        return search_res

    def tool_name(self) -> str:
        return "file_search"

    def _compress_contents(self, question: str, file_contents: List[Dict[str, Any]]):
        """使用大模型对contents进行压缩"""
        # 每个文件单独压缩
        compress_res = []
        for contents in file_contents:
            llm_input = compress_prompt.replace("$question", question).replace("$file_contents",
                                                                               str({'file_name': contents['file_name'],
                                                                                    'file_contents': contents[
                                                                                        'file_contents']}))
            llm = OpenAPI(temperature=0.01, api_base=OPENAPI["URL"], api_key=OpenapiContext.ak,
                          timeout=300, model='gpt-4o')
            completion = llm.complete(llm_input)
            res = completion.text
            compress_res.append(
                {'file_name': contents['file_name'], 'file_contents': [res], 'file_id': contents['file_id']})

        return compress_res


class ReadCheckTool(ITool):
    check_model: str

    def __init__(self, check_model: str):
        self.check_model = check_model

    def execute(self, question: str, **kwargs) -> Any:
        return self._check_has_enough_info(question, **kwargs)

    def _check_has_enough_info(self, question: str, file_content: str) -> bool:
        llm = OpenAPI(temperature=0.01, api_base=OPENAPI["URL"], api_key=OpenapiContext.ak,
                      timeout=300, model=self.check_model)
        llm_input = check_read_info_prompt.replace("$question", question).replace("$file_content", file_content)
        completion = llm.complete(llm_input)
        res = completion.text.replace('\n', '').strip()
        return '可以回答' == res

    def tool_name(self) -> str:
        return "read_check"
