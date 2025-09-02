import concurrent.futures
import functools
import re
import uuid
from typing import List, Union, Dict

from bella_openapi.entity.standard_domtree import StandardDomTree, StandardNode
from llama_index.core.schema import BaseNode

from common.tool.vector_db_tool import query_all_by_source
from init.settings import user_logger, CACHE
from bella_rag.schema.nodes import NodeWithScore
from bella_rag.schema.nodes import StructureNode, ImageNode, TabelNode, TextNode, DocumentNodeRelationship
from bella_rag.schema.nodes import is_contextual_node
from bella_rag.utils.cache_util import NodeLRUCache
from bella_rag.utils.trace_log_util import trace
from bella_rag.vector_stores.index import FIELD_RELATIONSHIPS

node_cache = NodeLRUCache(capacity=int(CACHE['CAPACITY']))
EMPTY_OCR_RESULT = '[图片OCR内容]\n无文字'


def dom2nodes(dom: StandardDomTree) -> List[BaseNode]:
    """
    1. 从根节点开始遍历，将每个节点转换为对应类型的BaseNode
    2. 为每个节点建立关系
    """
    nodes = []
    node_trans_recursion(node=dom.root, parent=None, trans_nodes=nodes)
    nodes = sorted(nodes, key=lambda node: parse_level(node.order_num_str))
    return nodes


def node_trans_recursion(node: StandardNode, parent: BaseNode, trans_nodes: List[StructureNode]):
    # 添加父子节点依赖关系
    children = []
    for child in node.children:
        # 表格类型输出为数组
        llama_index_node = to_llama_index_node(child)
        if isinstance(llama_index_node, StructureNode):
            children.append(llama_index_node)
            if parent is not None:
                if parent.doc_relationships.get(DocumentNodeRelationship.CHILD) is None:
                    parent.doc_relationships[DocumentNodeRelationship.CHILD] = []
                parent.doc_relationships[DocumentNodeRelationship.CHILD].append(llama_index_node)
                llama_index_node.doc_relationships[DocumentNodeRelationship.PARENT] = parent
            if child.children:
                node_trans_recursion(child, llama_index_node, trans_nodes)
        else:
            # 表格节点无子节点
            children.extend(llama_index_node)
            # 构建表格父子节点关系
            if parent is not None:
                if parent.doc_relationships.get(DocumentNodeRelationship.CHILD) is None:
                    parent.doc_relationships[DocumentNodeRelationship.CHILD] = []
                for table_node in llama_index_node:
                    parent.doc_relationships[DocumentNodeRelationship.CHILD].append(table_node)
                    table_node.doc_relationships[DocumentNodeRelationship.PARENT] = parent

    trans_nodes.extend(children)
    # 添加同级节点依赖关系（排除表格节点）
    childs_without_table = sorted([n for n in children if not isinstance(n, TabelNode) and not isinstance(n, List)]
                                  , key=functools.cmp_to_key(compare_order))
    if len(childs_without_table) < 2:
        return
    for i in range(len(childs_without_table)):
        if (i + 2 > len(childs_without_table)):
            break
        # 同一层级节点添加顺序信息
        childs_without_table[i].doc_relationships[DocumentNodeRelationship.NEXT] = childs_without_table[i + 1]
        childs_without_table[i + 1].doc_relationships[DocumentNodeRelationship.PREVIOUS] = childs_without_table[i]


def compare_order(x: StructureNode, y: StructureNode):
    return get_order_index(x.order_num_str) - get_order_index(y.order_num_str)


def get_order_index(order_num: str) -> int:
    indexs = order_num.split(".")
    return (int)(indexs[len(indexs) - 1])


def get_same_level_order(order_num: str, offset: int) -> str:
    indexs = order_num.split(".")
    new_order = int(indexs[-1]) + offset
    new_order_str = ".".join(indexs[:-1])
    return f"{new_order_str}.{new_order}" if new_order_str else str(new_order)


def get_table_previous_level(order_num: str) -> str:
    if '-' not in order_num:
        return order_num
    indexs = order_num.split(".")
    return ".".join(indexs[:-1])


def _format_dom_path(path: List[int]) -> str:
    if path is None:
        return ""
    return ".".join(str(p) for p in path)


def _format_cell_path(parent_path: List[int], cell_path: List[int]) -> str:
    if parent_path is None or cell_path is None:
        return ""
    return ".".join(str(p) for p in parent_path) + '.' + '-'.join(str(p) for p in cell_path)


def to_llama_index_node(node: StandardNode) -> Union[StructureNode, List[StructureNode]]:
    # 通过类型区分

    if node.element.type == "Figure" and node.element.image:
        ocr_result = " " if EMPTY_OCR_RESULT in node.element.text else node.element.text
        return ImageNode(
            order_num_str=_format_dom_path(node.path),
            image_url=node.element.image.url,
            token=node.tokens,
            image_ocr_result=ocr_result)

    elif node.element.type == "Table":
        table_nodes = []
        row_len = 0
        for row in node.element.rows:
            row_len = max(row_len, row.cells[0].path[0])

        matrix = [[] for _ in range(row_len)]
        for row in node.element.rows:
            for cell in row.cells:
                for row_num in range(cell.path[0], cell.path[1] + 1):
                    for column_num in range(cell.path[2], cell.path[3] + 1):
                        table_node = TabelNode(
                            text=cell.text,
                            order_num_str=_format_cell_path(node.path, cell.path),
                            token=sum(cell_node.tokens for cell_node in cell.nodes),
                            cell=cell,
                        )
                        # 构建表格单元格二维矩阵
                        matrix[row_num - 1].insert(column_num - 1, table_node)
                        table_nodes.append(table_node)
        # 构建表格单元格间关系
        build_table_relationships(matrix)
        return table_nodes
    else:
        return TextNode(
            order_num_str=_format_dom_path(node.path),
            text=node.element.text,
            token=node.tokens,
            content=node.element.text)


def build_table_relationships(matrix):
    for i in range(len(matrix)):
        for j in range(len(matrix[i])):
            user_logger.info(f'build table node, order name:{matrix[i][j].order_num_str}, location row : {i} col : {j}')
            if (i > 1 and len(matrix[i - 1]) > j):
                matrix[i][j].doc_relationships[DocumentNodeRelationship.UP] = matrix[i - 1][j]
                matrix[i - 1][j].doc_relationships[DocumentNodeRelationship.DOWN] = matrix[i][j]
            if (j > 1):
                matrix[i][j].doc_relationships[DocumentNodeRelationship.LEFT] = matrix[i][j - 1]
                matrix[i][j - 1].doc_relationships[DocumentNodeRelationship.RIGHT] = matrix[i][j]
            if (i < len(matrix) - 1 and len(matrix[i + 1]) > j):
                matrix[i][j].doc_relationships[DocumentNodeRelationship.DOWN] = matrix[i + 1][j]
                matrix[i + 1][j].doc_relationships[DocumentNodeRelationship.UP] = matrix[i][j]
            if (j < len(matrix[i]) - 1):
                matrix[i][j].doc_relationships[DocumentNodeRelationship.RIGHT] = matrix[i][j + 1]
                matrix[i][j + 1].doc_relationships[DocumentNodeRelationship.LEFT] = matrix[i][j]


def query_and_rebuild_nodes(key, value, nodes):
    # 读取文件下全部节点
    index_nodes = query_all_by_source(source_id=key)
    rebuild_node_dic = rebuild_nodes_from_index(key, index_nodes=index_nodes, origin_nodes=value)

    for i, node in enumerate(nodes):
        if node.node_id in rebuild_node_dic.keys():
            metadata = node.metadata
            nodes[i].node = rebuild_node_dic.get(node.node_id)
            # 原始metadata信息赋值
            nodes[i].node.metadata = metadata
            user_logger.info(f'query_and_rebuild_node node id : {node.node_id}')


def restore_relationships(nodes: List[NodeWithScore]):
    relation_node_docs = {}
    for score_node in nodes:
        node = score_node.node
        if is_contextual_node(node) or \
                (FIELD_RELATIONSHIPS in node.metadata.keys() and node.metadata.get(FIELD_RELATIONSHIPS)):
            source_id = node.metadata.get("source_id")
            relation_nodes = relation_node_docs.get(source_id, [])
            relation_nodes.append(node)
            relation_node_docs[source_id] = relation_nodes

    # 从热点缓存中读取
    cached_keys = []
    for key, value in relation_node_docs.items():
        if node_cache.file_cached(file_id=key):
            user_logger.info(f'restore_relationships from cache : {key}')
            for node in nodes:
                metadata = node.metadata
                cache_node = node_cache.get(key, node.node_id)
                if cache_node:
                    # 原始metadata信息赋值
                    cache_node.metadata = metadata
                    node.node = cache_node
            cached_keys.append(key)

    # 去除缓存过的key
    for cache_key in cached_keys:
        relation_node_docs.pop(cache_key)

    futures = []
    # 如果relation不为空，读取全量节点构建
    if relation_node_docs:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(relation_node_docs.items()), 100)) as executor:
            for key, value in relation_node_docs.items():
                user_logger.info(f'restore_relationships task : {key}')
                futures.append(executor.submit(query_and_rebuild_nodes, key, value, nodes))

    # 等待所有任务完成
    concurrent.futures.wait(futures)


@trace(step="rebuild_nodes_from_index", log_enabled=False)
def rebuild_nodes_from_index(source_id: str, index_nodes: List[BaseNode], origin_nodes: List[BaseNode]) -> Dict[
    str, BaseNode]:
    """
    从向量库索引内还原节点relation
    """
    res = {}
    # 构建原始节点字典
    for origin_node in origin_nodes:
        res[origin_node.node_id] = origin_node

    # 从元信息中提取节点relation信息
    node_map = {}
    context_node_map = {}
    node_relation_map = {}
    # 第一次遍历记录所有context节点，第二次遍历还原节点父子兄弟关系，包括context节点依赖
    for index_node in index_nodes:
        # 如果是上下文节点，则添加所有子节点信息进入
        if is_contextual_node(index_node):
            # 上下文节点
            new_context_node = TextNode(id_=index_node.node_id, text=index_node.get_content(),
                                        pos=index_node.pos, token=index_node.token,
                                        context_id=index_node.context_id,
                                        doc_relationships=index_node.doc_relationships,
                                        order_num_str=index_node.order_num_str, metadata=index_node.metadata)
            node_map[index_node.node_id] = new_context_node
            context_node_map[index_node.context_id] = new_context_node

    for index_node in index_nodes:
        if isinstance(index_node, StructureNode) and not is_contextual_node(index_node):
            node_id = index_node.node_id
            text = index_node.get_complete_content()
            relationships = index_node.metadata.get(FIELD_RELATIONSHIPS)
            node_relation_map[node_id] = relationships
            if is_table_node(relationships):
                new_node = TabelNode(id_=node_id, text=text, pos=index_node.pos, token=index_node.token,
                                     order_num_str=index_node.order_num_str, metadata=index_node.metadata,
                                     context_id=index_node.context_id, embedding=index_node.embedding)
            elif isinstance(index_node, ImageNode):
                new_node = ImageNode(id_=node_id, text=text, image_ocr_result=index_node.image_ocr_result,
                                     image_url=index_node.image_url, pos=index_node.pos, token=index_node.token,
                                     order_num_str=index_node.order_num_str, metadata=index_node.metadata,
                                     context_id=index_node.context_id, )
            else:
                new_node = TextNode(id_=node_id, text=text, pos=index_node.pos, token=index_node.token,
                                    order_num_str=index_node.order_num_str, metadata=index_node.metadata,
                                    context_id=index_node.context_id, )
            node_map[node_id] = new_node
            # 如果节点归属于某一段上下文，则添加进上下文节点的属性内
            if new_node.context_id and context_node_map.get(new_node.context_id):
                # 添加leaf节点到上下文节点的group里
                context_node_map[new_node.context_id] \
                    .doc_relationships[DocumentNodeRelationship.CONTEXTUAL_GROUP].append(new_node)
                # 添加上下文节点到leaf节点的contextual关系里
                new_node.doc_relationships[DocumentNodeRelationship.CONTEXTUAL] = context_node_map[new_node.context_id]

    # 重新构建节点关系信息
    visited = set()
    for node_id, node in node_map.items():
        build_relation_detect_single_direction_cycles(node_id, node_map, node_relation_map, visited)

    for node_id, node in node_map.items():
        # 当前子节点仅记录了一条，扩充全量子节点
        if node and node.doc_relationships.get(DocumentNodeRelationship.HEAD_CHILD):
            child = node.doc_relationships.get(DocumentNodeRelationship.HEAD_CHILD)[0]
            # 该关系仅用于全量子节点搜索，search完毕则移除
            del node.doc_relationships[DocumentNodeRelationship.HEAD_CHILD]
            node.doc_relationships[DocumentNodeRelationship.CHILD] = search_all_child_nodes(child)

        for i, origin_node in enumerate(origin_nodes):
            if origin_node.node_id == node_id:
                # 更新节点
                res[node_id] = node

    # 为表格节点mock父亲节点
    for node_id, node in node_map.items():
        if not node_has_table_child(node):
            continue

        # 检测到table节点，则mock一个空的父节点，并连接兄弟节点
        children = sorted(node.doc_relationships.get(DocumentNodeRelationship.CHILD), key=lambda x: x.pos)
        deal_table_nodes = []

        for child in children:
            if child in deal_table_nodes or not isinstance(child, TabelNode) or not child.order_num_str:
                continue

            # 查找所有同表格节点
            level = get_table_previous_level(node.order_num_str)
            table_nodes = [n for n in children if n.order_num_str.startswith(level)]
            mock_parent_node = mock_table_parent_node(table_nodes)

            # 查找前后节点
            previous_node = next((c for i, c in enumerate(children) if
                                  c not in table_nodes and len(children) > i + 1 and children[i + 1] in table_nodes),
                                 None)
            next_node = next((children[i + 1] for i, c in enumerate(children) if
                              c in table_nodes and len(children) > i + 1 and children[i + 1] not in table_nodes), None)

            if previous_node:
                previous_node.doc_relationships[DocumentNodeRelationship.NEXT] = mock_parent_node
                mock_parent_node.doc_relationships[DocumentNodeRelationship.PREVIOUS] = previous_node
            if next_node:
                next_node.doc_relationships[DocumentNodeRelationship.PREVIOUS] = mock_parent_node
                mock_parent_node.doc_relationships[DocumentNodeRelationship.NEXT] = next_node

            user_logger.info(f'mock table parent node:{child.id_}, order num:{level}')
            deal_table_nodes.extend(table_nodes)

    # 还原节点加到缓存里
    user_logger.info(f'query_and_rebuild_node put node into cache : {source_id}, size : {len(index_nodes)}')
    node_cache.put(source_id, [node for node in node_map.values()])

    return res


def node_has_table_child(node: BaseNode) -> bool:
    if not node.doc_relationships or not isinstance(node.doc_relationships.get(DocumentNodeRelationship.CHILD), list):
        return False

    for child in node.doc_relationships.get(DocumentNodeRelationship.CHILD):
        if isinstance(child, TabelNode):
            return True

    return False


def mock_table_parent_node(nodes: List[TabelNode]) -> TextNode:
    origin_parent = nodes[0].doc_relationships.get(DocumentNodeRelationship.PARENT)
    token = 0
    mock_parent_node = TextNode(id_=str(uuid.uuid4()), text='', token=token)
    for node in nodes:
        if origin_parent:
            origin_parent.doc_relationships[DocumentNodeRelationship.CHILD].remove(node)
        node.doc_relationships[DocumentNodeRelationship.PARENT] = mock_parent_node
        token += node.token
    mock_parent_node.token = token
    mock_parent_node.doc_relationships[DocumentNodeRelationship.CHILD] = nodes
    if origin_parent:
        mock_parent_node.doc_relationships[DocumentNodeRelationship.PARENT] = origin_parent
        origin_parent.doc_relationships[DocumentNodeRelationship.CHILD].append(mock_parent_node)
    return mock_parent_node


def build_relation_detect_single_direction_cycles(node_id, node_map, node_relation_map, visited):
    """
    还原节点关系，并检查是否有闭环，闭环仅出现在单向内
    递归会造成深度过高栈溢出，改为迭代
    """
    stack = [(node_id, None, False)]
    local_stack = set()

    while stack:
        current_node_id, current_relation_direction, processed = stack.pop()
        if processed:
            local_stack.remove(current_node_id)
            continue

        if current_node_id in visited:
            continue  # 已经处理过的节点

        visited.add(current_node_id)
        local_stack.add(current_node_id)

        node = node_map[current_node_id]
        relationships = node_relation_map.get(current_node_id, {})

        # 先将当前节点标记为已处理完子节点，之后再处理其子节点
        stack.append((current_node_id, current_relation_direction, True))
        for key, value in relationships.items():
            if isinstance(value, list):
                relation_nodes = []
                for n in value:
                    if not current_relation_direction or current_relation_direction == key:
                        stack.append((n, key, False))
                        if n in local_stack:
                            user_logger.warn(
                                f'find circle relation node:{current_node_id}, relations:{node_relation_map.get(current_node_id, {})}')
                        else:
                            relation_nodes.append(node_map.get(n))
                    else:
                        relation_nodes.append(node_map.get(n))
                if relation_nodes:
                    node.doc_relationships[DocumentNodeRelationship.get_relationship_by_value(key)] = relation_nodes
            else:
                if not current_relation_direction or current_relation_direction == key:
                    stack.append((value, key, False))
                    if value in local_stack:
                        user_logger.warn(
                            f'find circle relation node:{current_node_id}, relations:{node_relation_map.get(current_node_id, {})}')
                        continue
                node.doc_relationships[DocumentNodeRelationship.get_relationship_by_value(key)] = node_map.get(value)


def search_all_child_nodes(start_node) -> List[BaseNode]:
    """
    通过一个子节点查询全量子节点
    """
    has_search_nodes = set()
    stack = [start_node]
    all_nodes = []

    while stack:
        current_node = stack.pop()
        current_node_id = current_node.node_id

        if current_node_id not in has_search_nodes:
            has_search_nodes.add(current_node_id)
            all_nodes.append(current_node)

            # 当前节点非父子关系的relation
            for relation, node in current_node.doc_relationships.items():
                # 非平级节点关系，直接跳过
                if not DocumentNodeRelationship.is_same_level(relation.value):
                    continue
                if node.node_id not in has_search_nodes:
                    stack.append(node)

    return all_nodes


def is_table_node(relation_types: Dict) -> bool:
    return DocumentNodeRelationship.UP.value in relation_types.keys() \
        or DocumentNodeRelationship.DOWN.value in relation_types.keys() \
        or DocumentNodeRelationship.LEFT.value in relation_types.keys() \
        or DocumentNodeRelationship.RIGHT.value in relation_types.keys()


def parse_level(level):
    """
    解析层级字符串，返回一个元组，表格节点会被特殊处理
    """
    parts = re.split(r'[\.-]', level)
    return tuple(map(int, parts))
