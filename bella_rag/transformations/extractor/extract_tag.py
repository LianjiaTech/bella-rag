from llama_index.core import PromptTemplate, get_response_synthesizer, DocumentSummaryIndex, SelectorPromptTemplate, \
    ChatPromptTemplate
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.prompts import PromptType
from llama_index.core.prompts.utils import is_chat_model
from llama_index.core.response_synthesizers import ResponseMode

from app.models.knowledge_file_meta_model import KnowledgeFileMeta
from app.services import embed_model
from app.services.knowledge_file_meta_service import KnowledgeMetaService
from app.utils.llm_response_util import get_response_json_str
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
        "3. 无法回答输出空即可"
    ),
    role=MessageRole.SYSTEM,
)

SUMMARY_QUERY = (
    "此文本可以用哪些tag标签进行分类，请输出分类的标签已json格式：例如：[\"财务记账\",\"财务法规\"]"
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

TREE_SUMMARIZE_PROMPT_SEL = SelectorPromptTemplate(
    default_template=PromptTemplate(
        SUMMARY_RAG_TRIGGER_PROMPT, prompt_type=PromptType.SUMMARY
    ),
    conditionals=tree_summarize_conditionals,
)


def extract_tag_impl(file_id, documents):
    """
    提取tag信息，用于rag触发
    """
    response_synthesizer = get_response_synthesizer(response_mode=ResponseMode.TREE_SUMMARIZE, llm=llm,
                                                    streaming=False,
                                                    summary_template=TREE_SUMMARIZE_PROMPT_SEL
                                                    )
    doc_summary_index = DocumentSummaryIndex.from_documents(llm=llm, stream=False, embed_summaries=False,
                                                            embed_model=embed_model,
                                                            documents=documents,
                                                            response_synthesizer=response_synthesizer,
                                                            summary_query=SUMMARY_QUERY
                                                            )
    tag = doc_summary_index.get_document_summary(documents[0].get_doc_id())
    # 存储
    data = KnowledgeFileMeta(tag=get_response_json_str(tag), file_id=file_id)
    KnowledgeMetaService.save(data)
