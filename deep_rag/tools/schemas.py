from llama_index.core.tools import FunctionTool, ToolMetadata
from pydantic import BaseModel, Field

from app.common.contexts import OpenapiContext
from deep_rag.common import file_reader
from deep_rag.common.contexts import DeepRagContext
from deep_rag.common.file_tool import chunk_file_content
from deep_rag.prompt.tool import check_read_info_prompt, read_summary_prompt
from deep_rag.tools import file_search_tool, read_check_tool
from init.settings import user_logger, OPENAPI
from bella_rag.llm.openapi import OpenAPI
from bella_rag.utils.openapi_util import count_tokens, openapi_modelname_to_contextsize

logger = user_logger


def file_search(question, page) -> str:
    """返回可用的知识文件列表file_list及分页信息"""
    logger.info(
        f'start file search. question: {question}, page: {page}, file_ids: {str(DeepRagContext.file_ids)}, has searched files : {str(DeepRagContext.searched_files)}')
    file_ids = DeepRagContext.file_ids
    file_search_params = DeepRagContext.file_search_params
    res = file_search_tool.execute(question=question,
                                   file_ids=[f for f in file_ids if f not in DeepRagContext.searched_files], **file_search_params)
    searched_files = DeepRagContext.searched_files
    # 补充本次搜索记录到上下文
    for f in res:
        searched_files.append(f["file_id"])
    DeepRagContext.searched_files = searched_files
    return str(res)


def file_load(file_id) -> str:
    """加载选中文件的内容"""
    # 根据模型窗口大小设置的剩余token量
    model = read_check_tool.check_model
    model_max_tokens = openapi_modelname_to_contextsize(model)
    left_tokens = (model_max_tokens - count_tokens(check_read_info_prompt, model) - count_tokens(DeepRagContext.query,
                                                                                                 model)) * 0.9  # 留点buffer

    file_content = file_reader.read_file(file_id)
    if count_tokens(file_content) > left_tokens:
        logger.info(f'execute_read_file left tokens: {left_tokens}')
        content_chunks = chunk_file_content(file_content, left_tokens)
        for chunk in content_chunks:
            if read_check_tool.execute(DeepRagContext.query, file_content=chunk):
                return chunk  # 如果读取完无结果，设置为无答案
        # 如果读取完无结果，设置为无答案
        return "无答案"
    else:
        if read_check_tool.execute(DeepRagContext.query, file_content=file_content):
            return file_content
        else:
            return "无答案"


# 1. 定义输入参数模型
class SearchInput(BaseModel):
    """搜索工具参数规范"""
    question: str = Field(..., description="用户提问")
    page: int = Field(1, description="分页页码，默认第1页")


# 1. 定义输入参数模型
class FileReadInput(BaseModel):
    """文件读取工具参数规范"""
    file_id: str = Field(..., description="需要读取的文件id")


# 2. 工具schema封装 --------------------------------
search_metadata = ToolMetadata(
    name="file_search",
    description="返回可用的知识文件列表file_list及分页信息",
    fn_schema=SearchInput
)
search_tool = FunctionTool.from_defaults(fn=file_search, tool_metadata=search_metadata)


def file_load_and_summary(file_id: str):
    res = file_load(file_id)
    conclusion_llm = OpenAPI(temperature=0.01, api_base=OPENAPI["URL"], api_key=OpenapiContext.ak,
                             timeout=300, model='gpt-4o')
    if '无答案' in str(res):
        return '无相关内容'
    llm_input = read_summary_prompt.replace("$question", DeepRagContext.query).replace("$file_content", str(res))
    completion = conclusion_llm.complete(llm_input)
    res = completion.text.replace('\n', '').strip()
    return res


read_metadata = ToolMetadata(
    name="read_file",
    description="从知识文件列表中读取与用户提问相关的文件内容",
    fn_schema=FileReadInput
)
read_tool = FunctionTool.from_defaults(fn=file_load_and_summary, tool_metadata=read_metadata)

tool_list = [
    {
        "name": "file_search",
        "purpose": "查询与用户提问相关的文件列表，并返回文件内与提问相关的内容片段，可翻页查询",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "用户提问"
                },
                "page": {
                    "type": "integer",
                    "description": "分页检索序号（从1开始）"
                }
            },
            "required": ["question", "page"]
        },
        "output_type": "List[FileID]"
    },
    {
        "name": "read_file",
        "purpose": "读取指定文件的详细内容",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_id": {
                    "type": "string",
                    "description": "通过file_search获取的文件标识"
                }
            },
            "required": ["file_id"]
        },
        "output_type": "FileContent"
    }
]
