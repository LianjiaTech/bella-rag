from typing import List

from init.settings import user_logger
from bella_rag.schema.nodes import StructureNode, DocumentNodeRelationship
from bella_rag.utils.openapi_util import count_tokens


def node_token_compute(nodes: List[StructureNode]):
    user_logger.info(f"start compute node tokens. size:{len(nodes)}")
    for node in nodes:
        count_node_sum_token(node)


def count_node_sum_token(node: StructureNode) -> int:
    if not node:
        return 0

    # 如果节点的token已经计算过，直接返回
    if node.token is not None and node.token >= 0:
        return node.token

    # 获取节点的完整内容并计算token数
    node_content = node.get_complete_content()
    node_token = count_tokens(text=node_content)

    # 获取子节点列表
    children = node.doc_relationships.get(DocumentNodeRelationship.CHILD, [])
    if isinstance(children, StructureNode):
        children = [children]

    # 递归计算子节点的token数并累加
    for child in children:
        if child.token is not None and child.token >= 0:
            node_token += child.token
        else:
            node_token += count_node_sum_token(child)

    # 更新当前节点的token数
    node.token = node_token
    return node_token


def search_structure_all_nodes(node: StructureNode) -> List[StructureNode]:
    root = node
    # 搜索根节点
    while root.doc_relationships.get(DocumentNodeRelationship.PARENT):
        root = root.doc_relationships.get(DocumentNodeRelationship.PARENT)
    return deep_search(root)


def deep_search(node: StructureNode) -> List[StructureNode]:
    nodes = [node]
    children = node.doc_relationships.get(DocumentNodeRelationship.CHILD)
    if not children:
        return nodes

    if isinstance(children, StructureNode):
        nodes.extend(deep_search(children))
    else:
        for child in children:
            nodes.extend(deep_search(child))

    return nodes
