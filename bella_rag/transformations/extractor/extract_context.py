import json
import sys
import traceback
from typing import Tuple, List

from llama_index.core.prompts import PromptType

from app.services import chunk_vector_index_structure, embed_model
from app.services.chunk_content_attached_service import ChunkContentAttachedService
from app.services.context_service import redis_client, redis_key_prefix, save_context_chunk
from app.utils.llm_response_util import get_response_json_str
from common.tool.vector_db_tool import query_all_by_source
from init.settings import user_logger, CONTEXT_SUMMARY, OPENAPI
from bella_rag.llm.openapi import OpenAPI
from bella_rag.prompts.prompts import PromptTemplate
from bella_rag.schema.nodes import StructureNode, TabelNode, DocumentNodeRelationship
from bella_rag.utils.complete_util import _complete_table, complete_all_sub_nodes
from bella_rag.utils.openapi_util import count_tokens, DEFAULT_MODEL
from bella_rag.utils.schema_util import rebuild_nodes_from_index
from bella_rag.utils.trace_log_util import trace

llm = OpenAPI(model="gpt-4o", temperature=0, api_base=OPENAPI["URL"], api_key=OPENAPI["AK"], timeout=300, top_p=1,)

# todo summary prompt配到apollo里
contextual_prompt = '''
你是一个背景补全专家，你擅长结合整个文档对文档的每一部分补充一个背景信息，让文档的每一部分单独出现的时候信息都是完整的。
你会收到两个信息，文件名，文件内容分为几部分，包含文件内容的list， list的长度大于等于1，list中是文档的各个部分，在文档中顺序跟list中顺序一致。请你结合整个文档内容，为文档的每一部分补充一个简短的背景知识。

要求：
1、补全的背景信息需要满足以下条件：
-背景信息字数在50-100字，不要过于简短，也不要过长
-背景信息必须给出内容的出处，依赖的系统，背景尽量完整
-背景信息开头必须是内容来自文档名称 （文档格式信息可以忽略）
2、按照我给你的输出格式进行输出
3、不要输出分析内容
4、不要输出文档内容，直接输出背景信息
5. 输出为json, 禁止输出中suc_list的长度跟输入中content_list的list长度不相等，必须相等！！！！！
=========
输入: 
'file_name' : xxxx,
'content_len': K
'content_list': [
文档第1部分的内容,
文档第2部分的内容,
...,
文档第K部分的内容
]

输出:
{{{{
"suc_len": K
"suc_list": [
文档第1部分的背景信息,
文档第2部分的背景信息,
...,
文档第K部分的背景信息
]
}}}}

开始吧！
输入: 
'file_name' : {file_name},
'content_len': {content_len},
'content_list': {content_list},
输出:

'''

@trace(step="context_summary", progress="context_summary")
def context_summary(source_id: str):
    """
    上下文提取，构建context节点及索引
    """
    has_done = redis_client.get(redis_key_prefix + source_id)
    if has_done:
        user_logger.info("文件上下文已经提取完成file_id = %s", source_id)
        return

    # 检查文件是否结构化文档：某一节点包含层级信息
    structure_node_sample = ChunkContentAttachedService.find_structure_node(source_id, 1, 0)
    if not structure_node_sample:
        user_logger.info(f'file: {source_id} is not structured, skip context summary')
        return

    # 查询全量节点
    nodes = query_all_by_source(source_id, True)
    rebuild_node_dic = rebuild_nodes_from_index(source_id, index_nodes=nodes, origin_nodes=nodes)
    nodes = list(rebuild_node_dic.values())
    user_logger.info(f'start context summary: {source_id}, chunk size: {len(nodes)}')
    if not nodes:
        return

    file_name = nodes[0].metadata[chunk_vector_index_structure.doc_name_key]
    # 对节点进行分组
    user_logger.info(f'start group nodes : {source_id}')
    spilt_lis = spilt_nodes(nodes, int(CONTEXT_SUMMARY['SPILT_MAX_LENGTH']))
    grouped_nodes = merge_node_group(spilt_lis,
                                     int(CONTEXT_SUMMARY['MERGE_MIN_LENGTH']),
                                     int(CONTEXT_SUMMARY['MERGE_MAX_LENGTH']),
                                     int(CONTEXT_SUMMARY['FORCE_MERGE_LENGTH']))
    user_logger.info(f'finish group nodes : {source_id}, group size : {len(grouped_nodes)}')

    # 获取每个最小单元组的背景信息
    user_logger.info(f'start get background info : {source_id}')
    background_info_lis = get_background_info(grouped_nodes, source_id, 100000, 0)    # overlap设置为0，不允许重叠
    user_logger.info(f'finish get background info : {source_id}, background size: {len(background_info_lis)}')

    context_texts = []
    group_texts = []
    all_group_nodes = []
    # 进行summary分段总结
    for background_info in background_info_lis:
        nodes_to_summary = background_info[1]
        all_group_nodes.extend(background_info[1])
        user_logger.info(f'start summary contexts : {source_id}, context node size: {len(nodes_to_summary)}')
        # 模型总结每批最大大小
        summary_max_batch_size = int(CONTEXT_SUMMARY['SUMMARY_MAX_BATCH_SIZE'])
        batch_nodes = [nodes_to_summary[i:i + summary_max_batch_size]
                       for i in range(0, len(nodes_to_summary), summary_max_batch_size)]
        for batch in batch_nodes:
            cont_list = []
            for i, ready_nodes in enumerate(batch):
                # 拼接所有文本信息
                context_part = ''
                for ready_node in ready_nodes:
                    context_part += ready_node.get_complete_content()
                # llama-index内部模型调用对prompt做format，可能会识别到文档内部{}为变量导致冲突，替换为双括号
                cont_list.append(f'文档第{i + 1}部分：{context_part.replace("{", "{{").replace("}", "}}").strip()}')
            summary_res = summary_nodes(cont_list, file_name, source_id)
            if not summary_res:
                return
            context_texts.extend(summary_res)
            group_texts.extend(cont_list)

    order = 0
    # 构建context节点
    embeddings = embed_model.get_text_embedding_batch(context_texts)
    for i, context_text in enumerate(context_texts):
        sub_ids = []
        extra = {}
        for node in all_group_nodes[i]:
            if not extra:
                extra = node.extra_info
            sub_ids.append(node.node_id)

        context_id = f'{source_id}-context-{order}'
        save_context_chunk(source_id, file_name, context_text, context_id, sub_ids,
                           extra, embeddings[i], count_tokens(group_texts[i]))
        user_logger.info(f'save context chunk: {source_id}, context_id: {context_id}, content: {context_text}')
        order += 1

    user_logger.info(f'finish context summary: {source_id}')
    redis_client.set(redis_key_prefix + source_id, "done")


def summary_nodes(texts: List[str], file_name: str, source_id: str) -> List[str]:
    system_prompt = contextual_prompt.format(file_name=file_name,
                                             content_len=len(texts),
                                             content_list=texts)
    token_num = count_tokens(system_prompt)
    if token_num > 120000:
        user_logger.error(f'context summary failed. {source_id} context token too much : {token_num}')
        return []

    # 为防止summary个数与context不一致，新增重试
    max_retries = 3
    retry_count = 0
    context_texts = None
    context_summary_prompt = PromptTemplate(
        template=system_prompt,
        prompt_type=PromptType.QUESTION_ANSWER,
    )
    while retry_count < max_retries:
        try:
            res = llm.predict(prompt=context_summary_prompt)
            context_texts = json.loads(get_response_json_str(res)).get('suc_list')
            user_logger.info(f'finish summary contexts : {source_id}, context_texts: {context_texts}')

            # 检查数量是否一致
            if context_texts and len(context_texts) == len(texts):
                return context_texts
            else:
                user_logger.warn(
                    f'context summary failed. summary num : {len(context_texts)} context num : {len(texts)}')
        except Exception as e:
            user_logger.error(f'Error during context summary: {e}')
            traceback.print_exc()

        retry_count += 1

    if not context_texts or len(context_texts) != len(texts):
        # todo summary出来的context数量对不上怎么办？人工补偿
        user_logger.error(
            f'context summary failed after {max_retries} retries. summary num : {len(context_texts)} context num : {len(texts)}')
        return []


def spilt_nodes(nodes: List[StructureNode], spilt_max_length: int) -> List[Tuple[int, List[StructureNode]]]:
    """
    将文档节点做分组进行上下文总结
    每组节点的token数量不超过spilt_max_length
    表格进行全表补全

    输出结构：(token数，分组节点列表)
    """
    node_grouped = []
    added_list = []

    # 检验节点是否包含token及层级信息
    for node in nodes:
        if node.token and node.token < 0:
            return []

    # 遍历所有节点
    for node in nodes:
        if node in added_list:
            continue

        # 如果是表格节点，则全表补全
        ready_list = []
        if isinstance(node, TabelNode):
            table_parent = node.doc_relationships.get(DocumentNodeRelationship.PARENT)
            if not table_parent or table_parent.token > spilt_max_length:
                # 父节点token数高于最大限制，直接补全表
                table_str = _complete_table(node, sys.maxsize, ready_list, DEFAULT_MODEL)
                added_list.extend(ready_list)
                node_grouped.append((count_tokens(table_str), ready_list))
                continue
            else:
                # 寻找表格的最大父节点
                while table_parent:
                    index = table_parent.doc_relationships.get(DocumentNodeRelationship.PARENT)
                    if not index or index.token > spilt_max_length:
                        break
                    table_parent = index
                text_str = complete_all_sub_nodes(table_parent, ready_list, sys.maxsize, DEFAULT_MODEL)
                added_list.extend(ready_list)
                node_grouped.append((count_tokens(text_str), ready_list))
                continue

        # 如果节点token数直接超了，直接添加节点进去，后续merge
        if node.token > spilt_max_length:
            user_logger.info(f'split node token exceed. skip! : {node.node_id}')
            node_grouped.append((count_tokens(node.get_complete_content()), [node]))
            continue

        # 非表格节点，搜索最大token父节点
        parent_index = node
        while True:
            parent_node = parent_index.doc_relationships.get(DocumentNodeRelationship.PARENT)
            if parent_node in added_list:
                # 如果父节点已经分到其他上下文组里，则无视掉
                parent_node = None
            parent_sum_token = parent_node.token if parent_node else sys.maxsize

            if not parent_node or parent_index.token <= spilt_max_length < parent_sum_token:
                break
            parent_index = parent_node

        text_str = complete_all_sub_nodes(parent_index, ready_list, sys.maxsize, DEFAULT_MODEL)
        if parent_node:
            text_str = parent_node.get_complete_content() + '\n' + text_str
        added_list.extend(ready_list)
        node_grouped.append((count_tokens(text_str), ready_list))

    return node_grouped


def merge_node_group(groups: List[Tuple[int, List[StructureNode]]],
                     merge_min_length: int,
                     merge_max_length: int,
                     force_merge_length: int) -> List[List[StructureNode]]:
    """
    对拆分的节点做聚合操作，去除一些过小的分支
    必须合并的阈值 force_merge_length
    可以合并的阈值 merge_min_length
    最大token数 merge_max_length
    """
    def find_merge_index(index: int) -> int:
        # 合并规则，往左右token数较低的group里聚合
        if index == 0:
            merge_with_index = 1
        elif index == len(groups) - 1:
            merge_with_index = len(groups) - 2
        else:
            left_token_count = groups[index - 1][0]
            right_token_count = groups[index + 1][0]
            merge_with_index = index - 1 if left_token_count <= right_token_count else index + 1
        return merge_with_index

    while len(groups) > 1:
        # 找到需要合并的group
        merge_index = -1
        for i, (token_count, _) in enumerate(groups):
            if token_count < force_merge_length:
                merge_index = i
                break
            elif token_count < merge_min_length:
                index_ready_merge = find_merge_index(i)
                new_token_count = groups[index_ready_merge][0] + groups[i][0]
                if new_token_count <= merge_max_length:
                    merge_index = i
                    break

        # 如果没有需要合并的group，退出循环
        if merge_index == -1:
            break

        index_ready_merge = find_merge_index(merge_index)

        # 合并group
        groups[index_ready_merge] = (
            groups[index_ready_merge][0] + groups[merge_index][0],
            groups[index_ready_merge][1] + groups[merge_index][1]
        )

        # 删除已合并的group
        del groups[merge_index]

    return [group[1] for group in groups]


def get_background_info(group_nodes: List[List[StructureNode]],
                        source_id: str,
                        max_background_length: int,
                        overlap_length: int) -> List[Tuple[str, List[List[StructureNode]]]]:
    """
    对分好批的node节点做背景信息搜索，主要是防止背景信息过长一批放不下
    """
    # 1. 查询每个group的边界节点
    boundaries = []
    new_group_nodes = []
    for group_node in group_nodes:
        start = group_node[0]
        end = group_node[0]
        for node in group_node:
            if start.pos > node.pos:
                start = node
            if end.pos < node.pos:
                end = node

        boundaries.append((start, end))
        new_group_nodes.append(group_node)

    # 2. 查询文档的全量节点，计算token
    flat_nodes = [node for sub_nodes in group_nodes for node in sub_nodes]
    all_nodes = sorted(flat_nodes, key=lambda node: node.pos)

    # 3. 对节点分组，并寻找边界
    sub_groups = group_nodes_by_token_length(all_nodes, max_background_length, overlap_length)

    # 4. 背景信息分组
    result = []
    for node_group in sub_groups:
        group_end = node_group[-1].pos
        background_text = ''
        for node in node_group:
            background_text += node.get_complete_content()
        for i, boundary in enumerate(boundaries):
            if boundary[0].pos <= group_end <= boundary[1].pos:
                result.append((background_text, new_group_nodes[:i + 1]))
                del new_group_nodes[:i + 1]
                del boundaries[:i + 1]
                # 计算该背景信息内容
                break

    return result


def group_nodes_by_token_length(nodes: List[StructureNode],
                                max_length: int, overlap: int) -> List[List[StructureNode]]:
    node_tokens = {}
    for node in nodes:
        node_tokens[node.node_id] = count_tokens(node.get_complete_content())
    grouped_nodes = []
    current_group = []
    current_length = 0

    for node in nodes:
        node_length = node_tokens[node.node_id]
        if current_length + node_length > max_length:
            # 将当前组添加到分组列表中
            grouped_nodes.append(current_group)
            # 创建新的组，包含重叠部分
            overlap_length = 0
            while current_group and overlap_length < overlap:
                overlap_length += node_tokens[current_group.pop(0).node_id]
            current_group = current_group[-overlap_length:] if overlap_length > 0 else []
            current_length = sum(node_tokens[c.node_id] for c in current_group)

        current_group.append(node)
        current_length += node_length

    if current_group:
        grouped_nodes.append(current_group)

    return grouped_nodes

