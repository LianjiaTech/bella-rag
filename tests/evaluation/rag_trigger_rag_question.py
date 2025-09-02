import copy
import json
import os
import random

from llama_index.core import get_response_synthesizer, DocumentSummaryIndex, PromptTemplate
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.prompts import PromptType
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.core.tools import FunctionTool

from app.common.contexts import UserContext
from app.services import ak
from app.services.knowledge_file_meta_service import KnowledgeMetaService
from app.utils.llm_response_util import get_response_json_str
from init.settings import OPENAPI, VECTOR_DB_COMMON
from bella_rag.llm.openapi import OpenAPI, OpenAPIEmbedding
from bella_rag.transformations.factory import TransformationFactory
from bella_rag.utils.file_api_tool import file_api_client
from bella_rag.utils.file_util import get_file_type
from tests.evaluation.utils import fun, RagToolMetadata, Result, has_call_tool

"""
rag触发优化评测
"""

PROMPT = """# 角色
你是一个知识检索增强（RAG）相关能力测评的专家

# 目标
根据文件的内容生成两份数据：
- 提取出一份可以触发RAG工具的20个问题，用triggerRag为true标识。
- 制造一份与文章内容无关不应该触发RAG工具的5个闲聊类型的问题，用triggerRag为false标识。

# 背景
生成的Question用于是否能触发知识检索增强的测评，这对应RAG相关检索十分重要，影响到用户是否能唤起知识检索增强工具

# 限制条件
- 严格限制输出的集合里包含可以触发RAG工具的问题为20个，不应该触发RAG工具的问题为5个
- 用JSON数组格式输出最终的结果,直接输出结果，triggerRag为boolean类型的true/false，不是字符串类型
- 注意，仅返回最终的JSON结果，输出数据必须是JSON，不需要转为markdown标签包裹的json，不得返回任何其他信息！

# 输出格式示例：
[{{\"question":\"<question>\",\"triggerRag\":\"<triggerRag>\"}}]

# 文章内容
{context_str}
"""

QUESTION_SUMMARIZE_PROMPT = PromptTemplate(
    PROMPT, prompt_type=PromptType.CUSTOM
)

FILE_ID_LIST = [
    "F840191631436062720",
    "file-2503121724150021001365-960503137",
    "F812326354947043328",
    "F840191550344237056",
    "F840191502956425216",
    "F840191417690984448",
    "F840901876207374336",
    "F892808861055098880",
]

embed_model = OpenAPIEmbedding(model=VECTOR_DB_COMMON["EMBEDDING_MODEL"],
                               embedding_batch_size=VECTOR_DB_COMMON["EMBEDDING_BATCH_SIZE"],
                               api_key=ak, model_dimension=int(VECTOR_DB_COMMON["DIMENSION"]))

llm = OpenAPI(model="gpt-4o", temperature=0.01, api_base=OPENAPI["URL"], api_key=OPENAPI["AK"], timeout=300)

response_synthesizer = get_response_synthesizer(response_mode=ResponseMode.TREE_SUMMARIZE, llm=llm,
                                                summary_template=QUESTION_SUMMARIZE_PROMPT,
                                                streaming=False)


def test_rag_trigger_question():
    """构建评测集"""
    UserContext.user_id = "bella-rag"
    result_list = []
    for file_id in FILE_ID_LIST:
        file = file_api_client.get_file_info(file_id)
        file_type = get_file_type(file.get('filename'))
        documents = TransformationFactory.get_reader(file_type).load_file(file_id=file_id)
        doc_summary_index = DocumentSummaryIndex.from_documents(llm=llm, stream=False, embed_summaries=False,
                                                                embed_model=embed_model,
                                                                documents=documents,
                                                                response_synthesizer=response_synthesizer
                                                                )
        question_json = doc_summary_index.get_document_summary(documents[0].get_doc_id())
        question_json = get_response_json_str(question_json)
        question_list = json.loads(question_json)
        result = Result(questions=question_list, file_name=file.get('filename'))
        result_list.append(result)

    # 交叉填充问题
    for i, item in enumerate(result_list):
        current_questions = item.questions
        for other_item in result_list[:i] + result_list[i + 1:]:
            other_questions = other_item.questions
            # 随机选择一些问题添加到当前文件的问题列表中
            selected_questions = random.sample(other_questions, min(len(other_questions), 5))  # 例如，随机选择2个问题
            for question in selected_questions:
                if question not in current_questions:  # 确保不重复添加相同的问题
                    copy_question = copy.deepcopy(question)
                    copy_question['triggerRag'] = False
                    current_questions.append(copy_question)
                    if len(current_questions) >= 40:
                        break
    # 指定要写入的 JSON 文件名
    out_file_path = os.path.dirname(__file__) + "/result/rag_trigger_question.json"
    # 打开文件并写入 JSON 数据
    result_dicts = [result.json_response() for result in result_list]
    with open(out_file_path, 'w', encoding='utf-8') as f:
        json.dump(result_dicts, f, ensure_ascii=False, indent=4)


NO_OPTIMIZATION_PROMPT = "# 工具选取规则\n## 工具设定\n你有一个rag_generate工具和其他几个用户自定义的工具，其中rag_generate是一个高级工具，专为检索和综合用户上传文档中的信息而设计，它特别适合于需要访问特定和准确知识的专业领域，该工具通过搜索用户上传的知识文档来找到与用户查询问题相关的信息进行回答；每一个工具都会有函数功能和每个输入参数的详细描述信息。\n## 选取规则\nrag_generate工具选择条件: 当你发现用户提出的问题涉及到专业领域知识检索，你既无法直接通过已有知识进行回答，可以优先尝试调用rag_generate检索工具\n其他用户自定义工具选择条件: 当你发现用户提出的问题与某一个函数的功能描述高度匹配，或者用户的问题中可以获取到某一个工具必要的输入参数时，你可以调用这个工具\n不调用任何工具直接回答: 当用户提出的问题是通用的互联网知识时，你可以进行直接回答，不要调用工具。\n===========\n "


def test_rag_trigger_no_optimization():
    """未优化前的测试"""
    tools = [
        FunctionTool(
            fn=fun,
            metadata=RagToolMetadata(
                name="rag",
                description="可以用来查询已上传到这个助手的信息。如果用户正在引用特定的文件，那通常是一个很好的提示，这里可能有他们需要的信息。",
            )
        ),
        # 可以添加更多工具
    ]
    # 打开JSON文件
    with open(os.path.dirname(__file__) + "/result/rag_trigger_question.json", 'r', encoding='utf-8') as file:
        # 加载JSON数据
        question_data_list = json.load(file)
        result = []
        for question_data in question_data_list:
            questions = question_data['questions']
            for question_info in questions:
                chat_history = [ChatMessage(role=MessageRole.SYSTEM, content=NO_OPTIMIZATION_PROMPT)]
                chat_response = llm.chat_with_tools(user_msg=question_info['question'], chat_history=chat_history,
                                                    tools=tools)
                question_info["fileName"] = question_data['file_name']
                if has_call_tool(chat_response):
                    question_info['triggerRagResult'] = True
                else:
                    question_info['triggerRagResult'] = False
                if (question_info['triggerRagResult'] == True and question_info['triggerRag'] == True) or (
                        question_info['triggerRagResult'] == False and question_info['triggerRag'] == False):
                    question_info['triggerRagResultCorrect'] = True
                else:
                    question_info['triggerRagResultCorrect'] = False
                result.append(question_info)
    out_file_path = os.path.dirname(__file__) + "/result/rag_trigger_question_no_optimization.json"
    # 打开文件并写入 JSON 数据
    with open(out_file_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)


SUMMARY_PROMPT_OPTIMIZATION_PROMPT = """# 工具选取规则
## 工具设定
你有一个名为rag_generate的高级工具，专为检索用户上传文档中的信息而设计。该工具通过搜索用户上传的知识文档来找到与用户查询问题相关的信息进行回答。每一个工具都会有函数功能和每个输入参数的详细描述信息。
## 选取规则
rag_generate工具选择条件:
当用户提出的问题涉及以下文章信息时，必须调用rag_generate函数，不能自由回答，不能自由回答！！如果不涉及请不要调用rag_generate函数
文档名称：{document_name}
摘要：{summary}

其他用户自定义工具选择条件: 当你发现用户提出的问题与某一个函数的功能描述高度匹配，或者用户的问题中可以获取到某一个工具必要的输入参数时，你可以调用这个工具
不调用任何工具直接回答: 当用户提出的问题是通用的互联网知识时，你可以进行直接回答，不要调用工具。
===========
"""

# SUMMARY_PROMPT_OPTIMIZATION_PROMPT = """# 工具选取规则
# ## 工具设定
# 你有一个rag_generate工具和其他几个用户自定义的工具，其中rag_generate是一个高级工具，专为检索和综合用户上传文档中的信息而设计，它特别适合于需要访问特定和准确知识的专业领域，该工具通过搜索用户上传的知识文档来找到与用户查询问题相关的信息进行回答；每一个工具都会有函数功能和每个输入参数的详细描述信息。
# ## 选取规则
# rag_generate工具选择条件: 当用户提出的问题涉及以下文章信息时，必须调用rag_generate函数，不能自由回答！！如果不涉及请不要调用rag_generate函数
# 文档名称：{document_name}
# 摘要：{summary}
#
# 其他用户自定义工具选择条件: 当你发现用户提出的问题与某一个函数的功能描述高度匹配，或者用户的问题中可以获取到某一个工具必要的输入参数时，你可以调用这个工具
# 不调用任何工具直接回答: 当用户提出的问题是通用的互联网知识时，你可以进行直接回答，不要调用工具。
# ===========
# """

SUMMARY_OPTIMIZATION_PROMPT = """#工具选取规则
## 工具设定
你有一个rag_generate工具和其他几个用户自定义的工具。其中rag_generate是一个高级工具，专为检索用户上传文档中的信息而设计，该工具通过搜索用户上传的知识文档来找到与用户查询问题相关的信息进行回答；每一个工具都会有函数功能和每个输入参数的详细描述信息。
## rag_generate工具中用户上传文档中的信息概览
文档名称：{document_name}
标签：{tag}

## 选取规则
rag_generate工具选择条件: 当你发现用户提出的问题如果涉及rag_generate工具中用户上传文档中的信息，可以优先尝试调用rag_generate检索工具，如果不涉及请不要使用rag工具。
其他用户自定义工具选择条件: 当你发现用户提出的问题与某一个函数的功能描述高度匹配，或者用户的问题中可以获取到某一个工具必要的输入参数时，你可以调用这个工具
不调用任何工具直接回答: 当用户提出的问题是通用的互联网知识时，你可以进行直接回答，不要调用工具。
===========

"""


def test_rag_trigger_summary_optimization1():
    print(SUMMARY_OPTIMIZATION_PROMPT)


def test_rag_trigger_summary_optimization():
    """提取摘要的触发测试"""
    tools = [
        FunctionTool(
            fn=fun,
            metadata=RagToolMetadata(
                name="rag",
                description="专为检索用户上传文档中的信息而设计,用于增强知识检索",
            )
        ),
        # 可以添加更多工具
    ]
    # 打开JSON文件
    with open(os.path.dirname(__file__) + "/result/rag_trigger_question.json", 'r', encoding='utf-8') as file:
        # 加载JSON数据
        question_data_list = json.load(file)
        result = []
        for question_data in question_data_list:
            questions = question_data['questions']
            file_name = question_data['file_name']
            knowledge_file_meta = KnowledgeMetaService.get_by_file_id(file_name)
            for question_info in questions:
                prompt = SUMMARY_PROMPT_OPTIMIZATION_PROMPT.format(document_name=file_name,
                                                                   summary=knowledge_file_meta.summary_question,
                                                                   # tag=knowledge_file_meta.tag
                                                                   )
                chat_history = [ChatMessage(role=MessageRole.SYSTEM, content=prompt)]
                chat_response = llm.chat_with_tools(user_msg=question_info['question'], chat_history=chat_history,
                                                    tools=tools)
                question_info["fileName"] = question_data['file_name']
                if has_call_tool(chat_response):
                    question_info['triggerRagResult'] = True
                else:
                    question_info['triggerRagResult'] = False
                if (question_info['triggerRagResult'] == True and question_info['triggerRag'] == True) or (
                        question_info['triggerRagResult'] == False and question_info['triggerRag'] == False):
                    question_info['triggerRagResultCorrect'] = True
                else:
                    question_info['triggerRagResultCorrect'] = False
                result.append(question_info)
            # break
    out_file_path = os.path.dirname(__file__) + "/result/rag_trigger_question_summary_optimization.json"
    # 打开文件并写入 JSON 数据
    with open(out_file_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
