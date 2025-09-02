import time
from enum import Enum
from typing import List, Dict, Callable, Tuple

from llama_index.core.vector_stores import VectorStoreQuery
from tcvectordb.model.document import Filter

from app.common.contexts import query_embedding_context
from app.services import chunk_vector_index_structure
from common.helper.exception import UnsupportedTypeError
from common.tool.vector_db_tool import vector_store
from init.settings import user_logger
from bella_rag.schema.nodes import StructureNode, TabelNode, BaseNode, DocumentNodeRelationship, TextNode, \
    is_contextual_node
from bella_rag.utils.openapi_util import openapi_modelname_to_contextsize, count_tokens, str_token_limit, DEFAULT_MODEL
from bella_rag.utils.schema_util import get_table_previous_level
from bella_rag.utils.trace_log_util import trace
from bella_rag.vector_stores.types import MetadataFilter, FilterOperator, MetadataFilters

DEFAULT_GROUP = 'default'  # 默认节点分组，如果节点未关联任何上下文


class Small2BigModes(str, Enum):
    """Enum for different small to big modes."""

    MORE_INFO = "more_info"  # 尽量补全更多的内容
    MOST_COMPLETE = "most_complete"  # 确保补全内容完整连贯性
    CONTEXT_COMPLETE = "context_complete"  # 补全信息中添加上下文

    @staticmethod
    def get_small2big_mode_by_value(value: str):
        try:
            return Small2BigModes(value)
        except Exception:
            raise UnsupportedTypeError('unsupported small2big mode: ' + value)


@trace(step="small2big")
def small2big(nodes: List[BaseNode], chunk_max_length: int, model: str,
              mode: Small2BigModes = Small2BigModes.MOST_COMPLETE) -> List[BaseNode]:
    mode_function_map = {
        Small2BigModes.MORE_INFO: nodes_small2big_more_info,
        Small2BigModes.MOST_COMPLETE: nodes_small2big_most_complete,
        Small2BigModes.CONTEXT_COMPLETE: nodes_small2big_context_merge
    }

    if mode not in mode_function_map:
        raise ValueError(f"Invalid small to big mode: {mode}")

    return mode_function_map[mode](nodes, chunk_max_length, model)


def complete_nodes_individually(nodes: List[BaseNode], chunk_max_length: int, model: str,
                                complete_func: Callable[[StructureNode, int, List[BaseNode], str], str]
                                ) -> List[BaseNode]:
    """
    每个节点独立补全，节点间仅去重时存在关联
    """
    complete_res = []
    complete_nodes = []
    for n in nodes:
        new_node = n
        if isinstance(n, StructureNode):
            complete_content = complete_func(n, chunk_max_length, complete_nodes, model)
            new_node = TextNode(id_=n.node_id, text=complete_content,
                                pos=n.pos, token=n.token,
                                order_num_str=n.order_num_str, metadata=n.metadata,
                                context_id=n.context_id, doc_relationships=n.doc_relationships)
        if new_node.get_complete_content() != "":
            complete_res.append(new_node)
    return complete_res


def nodes_small2big_more_info(nodes: List[BaseNode], chunk_max_length: int, model: str) -> List[BaseNode]:
    return complete_nodes_individually(nodes, chunk_max_length, model, small2big_more_info)


def nodes_small2big_most_complete(nodes: List[BaseNode], chunk_max_length: int, model: str) -> List[BaseNode]:
    return complete_nodes_individually(nodes, chunk_max_length, model, small2big_most_complete)


def nodes_small2big_context_merge(nodes: List[BaseNode], chunk_max_length: int, model: str) -> List[BaseNode]:
    """
    先寻找提取每个节点待补全的ready list，然后做overlap去重
    """
    has_process_node = []
    nodes_ready_list = []
    # 需要先记录每个节点补全结果，待节点全处理完毕覆盖原内容
    nodes_complete_res = {}
    # 节点背景信息token量
    nodes_context_token = {}
    for node in nodes:
        if isinstance(node, StructureNode) and not is_contextual_node(node) and node.token < 0:
            user_logger.warn(f'structure node without token: {node.node_id}')
            complete_res = small2big_more_info(node, chunk_max_length, has_process_node, model)
            nodes_complete_res[node.node_id] = complete_res
            continue

        if is_contextual_node(node):
            context_lis = [node]
            context_lis.extend(node.doc_relationships.get(DocumentNodeRelationship.CONTEXTUAL_GROUP))
            # context节点先进行补全
            nodes_ready_list.insert(0, (node, context_lis))
        else:
            if node.token > chunk_max_length:
                user_logger.info(f"node:{node.node_id} length exceed chunk_max_length:{chunk_max_length}")
                # 直接补该节点下全量内容，最后截断
                nodes_ready_list.append((node, [node]))
            else:
                nodes_ready_list.append((node, search_node_complete_list(node, chunk_max_length)))

    query_embedding = query_embedding_context.get()
    # 对每个节点的ready list进行处理
    for item in nodes_ready_list:
        node = item[0]
        if is_contextual_node(node):
            complete_res = complete_contextual_node(node, chunk_max_length, has_process_node, query_embedding)
            nodes_complete_res[node.node_id] = complete_res
            continue

        if node in has_process_node:
            user_logger.info(f"node:{node.node_id} has been completed, skip!")
            continue

        ready_list = item[1]
        group_nodes = {}
        # 对leaf节点按照上下文进行分组
        for ready_node in ready_list:
            if ready_node in has_process_node:
                continue
            key = ready_node.context_id if ready_node.context_id and ready_node.doc_relationships.get(
                DocumentNodeRelationship.CONTEXTUAL) is not None else DEFAULT_GROUP
            group_nodes.setdefault(key, []).append(ready_node)

        content = ""
        for context_id, ready_nodes in group_nodes.items():
            # 如果group节点数仅包含mock节点，则跳过
            if any(not group_node.is_mock for group_node in ready_nodes):
                format_res = format_nodes_with_context(ready_nodes, context_id, chunk_max_length, has_process_node)
                nodes_context_token[node.node_id] = count_tokens(format_res[0])
                content += (format_res[0] + format_res[1])
                for ready_node in ready_nodes:
                    node.extend_complete_group_nodes(ready_node.get_complete_group_nodes())
        nodes_complete_res[node.node_id] = content

    complete_nodes = []
    # 填充每个节点的内容
    for node in nodes:
        complete_str = nodes_complete_res.get(node.node_id, '').strip()
        if complete_str:
            complete_str = nodes_complete_res.get(node.node_id, node.get_complete_content())
            if count_tokens(complete_str, model) > chunk_max_length + nodes_context_token.get(node.node_id, 0):
                user_logger.info(f"node complete too long, limit with token:{node.node_id}")
                complete_str = str_token_limit(text=complete_str, token_limit=chunk_max_length, model=model)

            new_node = TextNode(id_=node.node_id, text=complete_str, pos=node.pos, token=node.token,
                                order_num_str=node.order_num_str, metadata=node.metadata,
                                context_id=node.context_id, doc_relationships=node.doc_relationships)
            complete_nodes.append(new_node)
    return complete_nodes


def small2big_more_info(node: BaseNode, chunk_max_length: int, has_process_node: List[BaseNode], model: str) -> str:
    if not node or node in has_process_node:
        return ""
    node_record = {}
    # 搜索所有需要补全的节点
    search_node_texts(node, chunk_max_length, has_process_node, model, node_record)
    # 对搜索节点进行顺序拼接
    content = ""
    positions = sorted(node_record.keys())
    user_logger.info(f"_small2big : {node.node_id} search node size : {len(node_record)}")
    for pos in positions:
        content += node_record.get(pos)
    return content


def search_node_texts(node: BaseNode, chunk_max_length: int, has_process_node: List[BaseNode], model: str,
                      node_record: Dict[int, str]) -> List[str]:
    # 非结构化节点直接输出，不做补全
    if not isinstance(node, StructureNode):
        return []

    node_texts = []
    if isinstance(node, TabelNode):
        content = '\n' + _complete_table(node, chunk_max_length, has_process_node, model) + '\n'
    else:
        content = node.get_complete_content()

    content_tokens = count_tokens(content, model)
    if content_tokens > chunk_max_length:
        return []

    node_record[node.pos] = content
    has_process_node.append(node)
    node.extend_complete_group_nodes([node])
    node_texts.append(content)

    # 递归补全：子节点 -> 同级节点 -> 父节点
    parent = node.doc_relationships.get(DocumentNodeRelationship.PARENT)
    children = node.doc_relationships.get(DocumentNodeRelationship.CHILD)
    next_node = node.doc_relationships.get(DocumentNodeRelationship.NEXT)
    prev_node = node.doc_relationships.get(DocumentNodeRelationship.PREVIOUS)

    # 向下补全
    for child in children or []:
        if child not in has_process_node:
            texts = search_node_texts(child, chunk_max_length - content_tokens, has_process_node, model, node_record)
            content_tokens += _count_texts_token(texts, model)
            node_texts.extend(texts)
            node.extend_complete_group_nodes(child.get_complete_group_nodes())

    # 向前补全
    # 定义补全边界， 如果没有父亲节点，不做同级补全
    if parent:
        if prev_node and prev_node not in has_process_node:
            texts = search_node_texts(prev_node, chunk_max_length - content_tokens, has_process_node, model, node_record)
            content_tokens += _count_texts_token(texts, model)
            node_texts.extend(texts)
            node.extend_complete_group_nodes(prev_node.get_complete_group_nodes())

        # 向上补全
        if parent not in has_process_node:
            texts = search_node_texts(parent, chunk_max_length - content_tokens, has_process_node, model, node_record)
            content_tokens += _count_texts_token(texts, model)
            node_texts.extend(texts)
            node.extend_complete_group_nodes(parent.get_complete_group_nodes())

        # 向后补全
        if next_node and next_node not in has_process_node:
            texts = search_node_texts(next_node, chunk_max_length - content_tokens, has_process_node, model, node_record)
            content_tokens += _count_texts_token(texts, model)
            node_texts.extend(texts)
            node.extend_complete_group_nodes(next_node.get_complete_group_nodes())

    return node_texts


def _count_texts_token(texts: List[str], model: str) -> int:
    count = 0
    for text in texts:
        count += count_tokens(text, model)
    return count


def xstr(s):
    return '' if s is None else str(s)


def get_table_header_node(node: TabelNode) -> TabelNode:
    # 寻找表头节点，默认为第一行节点
    while node.doc_relationships.get(DocumentNodeRelationship.UP) is not None:
        node = node.doc_relationships.get(DocumentNodeRelationship.UP)
    return node


def _complete_table(table_node: TabelNode, chunk_max_length: int, has_process_node: List[BaseNode], model: str) -> str:
    def process_relationships(node: TabelNode, direction: str, initial_content: str) -> str:
        content = initial_content
        relationship_node = node.doc_relationships.get(direction)
        while relationship_node and relationship_node not in has_process_node:
            row_content = _complete_table_row(relationship_node, has_process_node, False)
            if chunk_max_length < count_tokens(first_line_content + content + row_content, model):
                return content
            if direction == DocumentNodeRelationship.UP:
                content = row_content + "\n" + content
            else:
                content = content + "\n" + row_content
            relationship_node = relationship_node.doc_relationships.get(direction)
        return content

    if table_node in has_process_node:
        return ""

    # 先补表头（默认为第一行，后续可根据解析字段）
    table_header_node = get_table_header_node(table_node)
    # 表头允许重复补
    first_line_content = _complete_table_row(table_header_node, has_process_node, True)

    # 表格节点，先补全为行，再按照行上下补
    row_content = ''
    if table_header_node.node_id != table_node.node_id:
        row_content = _complete_table_row(table_node, has_process_node, table_header_node.node_id == table_node.node_id)
    if chunk_max_length < count_tokens(first_line_content + row_content, model):
        # 如果这行内容超了，直接返回单元格内容
        table_node.doc_relationships[DocumentNodeRelationship.COMPLETE_GROUP] = {table_node}
        return table_node.get_complete_content()

    # 处理向上的关系
    row_content = process_relationships(table_node, DocumentNodeRelationship.UP, row_content)

    # 处理向下的关系
    row_content = process_relationships(table_node, DocumentNodeRelationship.DOWN, row_content)

    return first_line_content + row_content


def _complete_table_row(row_node: TabelNode, has_process_node: List[BaseNode], is_table_header: bool) -> str:
    def process_side(node: TabelNode, direction: str, initial_content: str, initial_line: str) -> (str, str):
        content = initial_content
        markdown_line = initial_line
        relationship_node = node.doc_relationships.get(direction)
        while relationship_node:
            has_process_node.append(relationship_node)
            node.extend_complete_group_nodes([relationship_node])
            if direction == DocumentNodeRelationship.LEFT:
                content = relationship_node.get_complete_content() + markdown_spliter + content
                markdown_line = markdown_table_dashed + markdown_spliter + markdown_line
            else:
                content = content + markdown_spliter + relationship_node.get_complete_content()
                markdown_line = markdown_line + markdown_spliter + markdown_table_dashed
            relationship_node = relationship_node.doc_relationships.get(direction)
        if direction == DocumentNodeRelationship.LEFT:
            content = markdown_spliter + content
            markdown_line = markdown_spliter + markdown_line
        else:
            content = content + markdown_spliter
            markdown_line = markdown_line + markdown_spliter
        return content, markdown_line

    content = row_node.get_complete_content()
    has_process_node.append(row_node)
    row_node.extend_complete_group_nodes([row_node])
    # 表格markdown分隔行
    markdown_table_dashed = "----"
    markdown_spliter = "|"
    markdown_line = markdown_table_dashed

    # 处理左侧关系
    content, markdown_line = process_side(row_node, DocumentNodeRelationship.LEFT, content, markdown_line)

    # 处理右侧关系
    content, markdown_line = process_side(row_node, DocumentNodeRelationship.RIGHT, content, markdown_line)

    # 如果为首行，需要markdown首行换行符
    if is_table_header:
        content = content + "\n" + markdown_line
    return content


def _chunk_max_tokens(model_name: str, system_prompt: str, query: str, threshold: float) -> int:
    # chunk长度计算规则：
    # 单条recall token_limit =(llm最大token数 - system实际token数 - query实际token数 - reply及上下文预留token数(40%)) ÷ 召回条数topN
    return openapi_modelname_to_contextsize(model_name) * threshold - count_tokens(system_prompt,
                                                                                   model_name) - count_tokens(
        query, model_name)


def small2big_most_complete(node: BaseNode, chunk_max_length: int, has_process_node: List[BaseNode], model: str) -> str:
    """
    搜索策略：
    （1）查询支持最大token量的父节点，拉取父节点全部内容
    （2）从该父节点的兄弟节点进行内容补全
    （3）表格节点全量补齐
    """
    if not node or node in has_process_node:
        return ""

    # 如果节点没有token信息，使用more info策略补全
    if is_contextual_node(node):
        result = complete_contextual_node(node, chunk_max_length, has_process_node, query_embedding_context.get())
    elif isinstance(node, StructureNode) and node.token < 0:
        result = small2big_more_info(node, chunk_max_length, has_process_node, model)
    else:
        result = most_complete_node_texts(node, chunk_max_length, has_process_node, model)

    if count_tokens(result, model) > chunk_max_length:
        user_logger.info(f"node complete too long, limit with token:{node.node_id}")
        result = str_token_limit(text=result, token_limit=chunk_max_length, model=model)
    return result


def most_complete_node_texts(node: BaseNode, chunk_max_length: int, has_process_node: List[BaseNode],
                             model: str) -> str:
    # 非结构化节点直接输出，不做补全
    if not isinstance(node, StructureNode):
        return ""

    # 节点内容超过最大补全长度，补全节点及全部子节点，限制max length
    if node.token > chunk_max_length:
        user_logger.info(f"node:{node.node_id} length exceed chunk_max_length:{chunk_max_length}")
        return complete_all_sub_nodes(node, has_process_node, chunk_max_length, model)

    content = ''
    ready_list = search_node_complete_list(node, chunk_max_length)
    # 从待补全的节点中，拼接所有内容
    for ready_node in ready_list:
        start = int(time.time() * 1000)
        content += complete_all_sub_nodes(ready_node, has_process_node, chunk_max_length, model) + "\n"
        node.extend_complete_group_nodes(ready_node.get_complete_group_nodes())
        user_logger.info(f'complete_all_sub_nodes cost:{int(time.time() * 1000) - start}, node id:{ready_node.node_id}')
    return content


def search_node_complete_list(node: BaseNode, chunk_max_length: int) -> List[BaseNode]:
    """
    补全可容纳token数最大且内容最完整的节点列表
    """
    # 搜索最大长度父节点
    parent_index = node
    while parent_index.doc_relationships.get(DocumentNodeRelationship.PARENT) \
            and parent_index.doc_relationships.get(DocumentNodeRelationship.PARENT).token <= chunk_max_length:
        parent_index = parent_index.doc_relationships.get(DocumentNodeRelationship.PARENT)

    # 从该父节点同级从左到右搜索内容
    ready_list = [parent_index]
    # 如果该节点已无父层级，则无需补同级兄弟节点
    # 判断是否有父层级关系，或者当前节点不是TabelNode类型的根节点
    has_parent = parent_index.doc_relationships.get(DocumentNodeRelationship.PARENT) is not None
    is_tabel_node_root = parent_index == node and isinstance(node, TabelNode)

    if has_parent or not is_tabel_node_root:
        left = parent_index.doc_relationships.get(DocumentNodeRelationship.PREVIOUS)
        right = parent_index.doc_relationships.get(DocumentNodeRelationship.NEXT)
        current_token = get_node_token(parent_index)
        while current_token <= chunk_max_length:
            sum_token = current_token
            if left is None and right is None:
                break

            if left and (get_node_token(left) + sum_token) <= chunk_max_length:
                sum_token += get_node_token(left)
                ready_list.insert(0, left)
                left = left.doc_relationships.get(DocumentNodeRelationship.PREVIOUS)

            if right and (get_node_token(right) + sum_token) <= chunk_max_length:
                sum_token += get_node_token(right)
                ready_list.append(right)
                right = right.doc_relationships.get(DocumentNodeRelationship.NEXT)

            if current_token == sum_token:
                break
            current_token = sum_token

        # 如果已补到最左节点且token还有余量，则补上父节点
        if not left and parent_index.doc_relationships.get(DocumentNodeRelationship.PARENT) \
                and current_token + count_tokens(parent_index.doc_relationships.get(
            DocumentNodeRelationship.PARENT).get_complete_content()) <= chunk_max_length:
            # mock一个仅包含文本无relation的父节点
            content = parent_index.doc_relationships.get(DocumentNodeRelationship.PARENT).get_complete_content()
            mock_parent_node = TextNode(text=content, is_mock=True,
                                        context_id=parent_index.doc_relationships.get(
                                            DocumentNodeRelationship.PARENT).context_id)
            ready_list.insert(0, mock_parent_node)

    return ready_list


def get_node_token(node: StructureNode) -> int:
    if node and node.token and node.token >= 0:
        return node.token
    return count_tokens(node.get_complete_content())


def complete_all_sub_nodes(node: StructureNode, has_process_node: List[BaseNode], chunk_max_length: int,
                           model: str) -> str:
    if node in has_process_node:
        return ""

    if isinstance(node, TabelNode):
        return '\n' + _complete_table(node, chunk_max_length, has_process_node, model) + '\n'

    content = node.get_complete_content()
    has_process_node.append(node)
    node.extend_complete_group_nodes([node])
    child = node.doc_relationships.get(DocumentNodeRelationship.CHILD)

    if isinstance(child, StructureNode):
        children = [child]
    else:
        children = child

    if children:
        children = sorted(children, key=lambda x: x.pos)
        for child in children:
            content += complete_all_sub_nodes(child, has_process_node, chunk_max_length, model)
            node.extend_complete_group_nodes(child.get_complete_group_nodes())

    return content


def complete_contextual_node(context_node: StructureNode, chunk_max_length: int,
                             has_process_node: List[BaseNode], query_embedding: List[float]) -> str:
    """
    补全上下文节点，不受token数限制，直接补全量related节点
    """
    sum_token = 0
    content = '背景信息：' + context_node.get_complete_content() + '\n参考内容：\n'
    sum_token += count_tokens(content)
    contextual_nodes = context_node.doc_relationships.get(DocumentNodeRelationship.CONTEXTUAL_GROUP)
    for node in contextual_nodes:
        if isinstance(node, TabelNode):
            if node in has_process_node:
                continue

            # 如果可以容下全量表格，则直接全量添加
            table_parent = node.doc_relationships.get(DocumentNodeRelationship.PARENT)
            table_token = table_parent.token if table_parent else context_node.token
            if table_token + sum_token <= chunk_max_length or not query_embedding:
                table_content = _complete_table(node, chunk_max_length, has_process_node, DEFAULT_MODEL) + '\n'
            else:
                all_table_nodes = table_parent.doc_relationships.get(DocumentNodeRelationship.CHILD) \
                    if table_parent else context_node.doc_relationships.get(DocumentNodeRelationship.CONTEXTUAL_GROUP)
                table_content = complete_table_by_row_similarity(query_embedding, node, chunk_max_length,
                                                                 has_process_node, all_table_nodes, sum_token)
            content += table_content
            sum_token += count_tokens(table_content)
            context_node.extend_complete_group_nodes(node.get_complete_group_nodes())
        else:
            content += node.get_complete_content()
            sum_token += count_tokens(node.get_complete_content())
            has_process_node.append(node)
            context_node.extend_complete_group_nodes([node])
    return content


def complete_table_by_row_similarity(query_embedding: List[float], node: TabelNode, chunk_max_length: int,
                                     has_process_node: List[BaseNode], all_table_nodes: List[StructureNode],
                                     sum_token: int) -> str:
    content = ""
    # 取相似度最高的行补全
    table_id = get_table_previous_level(node.order_num_str)
    source_id = node.metadata.get(chunk_vector_index_structure.doc_id_key)
    # 构建向量库extra表格查询条件
    query_filter = Filter(f'{chunk_vector_index_structure.extra_key} include (\"table_id:{table_id}\")')
    query_filter.And(f'source_id in (\"{source_id}\")')
    filters = [MetadataFilter(key=chunk_vector_index_structure.extra_key, value=[f'table_id:{table_id}'],
                              operator=FilterOperator.ANY),
               MetadataFilter(key=chunk_vector_index_structure.doc_id_key, value=source_id,
                              operator=FilterOperator.EQ)]
    metadata_filters = MetadataFilters(filters=filters)
    vector_store_query = VectorStoreQuery(similarity_top_k=500, query_embedding=query_embedding,
                                          filters=metadata_filters)
    nodes = vector_store.query(vector_store_query, chunk_vector_index_structure).nodes
    if not nodes:
        table_content = _complete_table(node, chunk_max_length, has_process_node, DEFAULT_MODEL) + '\n'
        return content + table_content

    user_logger.info(f'start complete node with highest score table id: {table_id}')
    all_table_map = {}
    for table_node in all_table_nodes:
        all_table_map[table_node.node_id] = table_node

    # 逐行补全直到token超限
    # 先补表头（默认为第一行，后续可根据解析字段）
    table_header_node = get_table_header_node(node)
    # 表头允许重复补
    first_line_content = _complete_table_row(table_header_node, has_process_node, True) + "\n"
    node.extend_complete_group_nodes(table_header_node.get_complete_group_nodes())
    content += first_line_content
    sum_token += count_tokens(first_line_content)
    for table_node in nodes:
        if all_table_map[table_node.node_id] in has_process_node:
            continue
        row_content = _complete_table_row(all_table_map[table_node.node_id], has_process_node, False) + "\n"
        row_token = count_tokens(row_content)
        if sum_token + row_token > chunk_max_length:
            return content
        content += row_content
        sum_token += row_token
        node.extend_complete_group_nodes(all_table_map[table_node.node_id].get_complete_group_nodes())

    return content


def format_nodes_with_context(group_nodes: List[StructureNode], group_id: str, chunk_max_length: int,
                              has_process_node: List[StructureNode]) -> Tuple[str, str]:
    """
    对属于一个group的节点进行format，返回背景str和leaf节点内容补全content
    """
    if not group_nodes:
        return "", ""

    # nodes进行排序
    group_nodes = sorted(group_nodes, key=lambda x: x.pos)
    context_str = ""
    if group_id != DEFAULT_GROUP:
        context_str = '背景信息：' + group_nodes[0].doc_relationships.get(
            DocumentNodeRelationship.CONTEXTUAL).get_complete_content() + '\n参考内容：\n'

    content = ""
    for node in group_nodes:
        if isinstance(node, TabelNode):
            if node in has_process_node:
                continue
            content = content + _complete_table(node, chunk_max_length, has_process_node, DEFAULT_MODEL) + '\n'
        else:
            content += complete_all_sub_nodes(node, has_process_node, chunk_max_length, DEFAULT_MODEL)

    if not content.replace('\n', ''):
        return "", ""
    return context_str, content
