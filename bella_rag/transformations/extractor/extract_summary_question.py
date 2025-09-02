from typing import Sequence, Optional

from llama_index.core import PromptTemplate, get_response_synthesizer, DocumentSummaryIndex, SelectorPromptTemplate, \
    ChatPromptTemplate
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.prompts import PromptType
from llama_index.core.prompts.utils import is_chat_model
from llama_index.core.response_synthesizers import ResponseMode
from llama_index.core.schema import Document
from llama_index.core.llms.llm import LLM as LLMPredictorType
from llama_index_client import BasePromptTemplate

from app.common.contexts import UserContext
from common.helper.exception import BusinessError
from init.settings import OPENAPI
from bella_rag.llm.openapi import OpenAPI

llm = OpenAPI(model="gpt-4o", temperature=0.01, api_base=OPENAPI["URL"], api_key=OPENAPI["AK"], timeout=300)

SUMMARY_RAG_TRIGGER_PROMPT = (
    "以下是来自多个来源的上下文信息。\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "根据来自多个来源的信息，而不是先前的知识， "
    "回答以下问题。\n"
    "问题：{query_str}\n"
    "回答： "
)

TEXT_QA_SYSTEM_PROMPT = ChatMessage(
    content=(
        "你是一个被全世界信任的专家问答系统。\n"
        "始终使用提供的上下文信息回答问题， "
        "而不是先前的知识。\n"
        "需要遵循的一些规则：\n"
        "1. 绝不要在回答中直接引用给定的上下文。\n"
        "2. 避免使用诸如'根据上下文，...'或'上下文信息...'或任何类似的表述。\n"
        "3. 使用中文输出结果。\n"
        "4. 不要给出无法回答的原因，输出空字符串即可"
    ),
    role=MessageRole.SYSTEM,
)

DEFAULT_SUMMARY_QUERY = (
    "描述所提供的文本是关于什么的。 "
    "此外，再描述一些本文可以回答的问题。"
)

# Tree Summarize
TREE_SUMMARIZE_PROMPT_TMPL_MSGS = [
    TEXT_QA_SYSTEM_PROMPT,
    ChatMessage(
        content=SUMMARY_RAG_TRIGGER_PROMPT,
        role=MessageRole.USER,
    ),
]

CHAT_TREE_SUMMARIZE_PROMPT = ChatPromptTemplate(
    message_templates=TREE_SUMMARIZE_PROMPT_TMPL_MSGS
)

tree_summarize_conditionals = [(is_chat_model, CHAT_TREE_SUMMARIZE_PROMPT)]

DEFAULT_TREE_SUMMARIZE_PROMPT_SEL = SelectorPromptTemplate(
    default_template=PromptTemplate(
        SUMMARY_RAG_TRIGGER_PROMPT, prompt_type=PromptType.SUMMARY
    ),
    conditionals=tree_summarize_conditionals,
)

"""
封装为执行模板代码，llmaIndex允许传入的值，但次方法不允许配置的均是有坑的，已帮助屏蔽了
embed_model 是llamaIndex留下的坑，即使embed_summaries=False也必须传递否则报错
"""


def run(documents: Sequence[Document],
        user: str,
        llm: LLMPredictorType,
        embed_model: Optional[BaseEmbedding] = None,
        tree_summarize: ResponseMode = ResponseMode.TREE_SUMMARIZE,
        summary_template: Optional[BasePromptTemplate] = DEFAULT_TREE_SUMMARIZE_PROMPT_SEL,
        summary_query: Optional[str] = DEFAULT_SUMMARY_QUERY):
    # 设置UID到context，embedding和模型请求会使用
    UserContext.user_id = user
    """
    提取总结信息，摘要+question
    """
    response_synthesizer = get_response_synthesizer(response_mode=tree_summarize,
                                                    llm=llm,
                                                    streaming=False,
                                                    summary_template=summary_template
                                                    )
    doc_summary_index = DocumentSummaryIndex.from_documents(llm=llm, stream=False, embed_summaries=True,
                                                            embed_model=embed_model,
                                                            documents=documents,
                                                            response_synthesizer=response_synthesizer,
                                                            summary_query=summary_query
                                                            )
    summary_question = doc_summary_index.get_document_summary(documents[0].get_doc_id())

    # 如果summary_question是空 手动抛出异常
    if not summary_question:
        raise BusinessError("extract_summary_question 模型总结是空")
    return summary_question
