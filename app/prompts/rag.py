from typing import List, Optional

from llama_index.core.prompts import PromptType

from app.plugin.plugins import Plugin, GeneratePlugin
from bella_rag.prompts.prompts import PromptTemplate


show_quote_constraint = \
"""
# 引用要求:
- 以格式 '<sup>[i]</sup> <sup>[j]</sup>'插入引用，其中 i, j 是所引用内容的 参考信息序号，并用 '<sup>[' 和 ']</sup>' 包裹。
- 在句子末尾插入引用，每个句子最多 4 个引用。
- 如果答案内容不来自检索到的文本块，则不要插入引用。\n
"""

def get_rag_template(instructions: str, plugins: Optional[List[Plugin]] = [], show_quote: bool = False) -> PromptTemplate:
    prompt = "请扮演给出的角色，根据上下文信息，以中文回答问题，不知道如实回答不知道，不要创造答案\n"
    # 根据模版参数，添加约束
    if show_quote:
        prompt += show_quote_constraint

    # 从plugin内读取prompt的约束，依次添加
    for plugin in plugins:
        if isinstance(plugin, GeneratePlugin) and plugin.get_prompt_constraint():
            prompt += plugin.get_prompt_constraint()
            break

    # 添加变量
    prompt += "===========\n{roleInfo}\n===========\n{recallInfo}"
    if instructions.find('{recallInfo}') != -1:
        # 如果用户上传提示词为recall模板，直接替换
        prompt = instructions
    return PromptTemplate(
        prompt,
        prompt_type=PromptType.QUESTION_ANSWER,
    )
