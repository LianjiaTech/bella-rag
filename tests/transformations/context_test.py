from bella_rag.schema.nodes import TextNode
from bella_rag.transformations.extractor.extract_context import merge_node_group


def test_merge_node_group():
    nodes1 = [TextNode(id_='node1'), TextNode(id_='node2')]
    nodes2 = [TextNode(id_='node3')]
    nodes3 = [TextNode(id_='node4'), TextNode(id_='node5')]
    nodes4 = [TextNode(id_='node6')]

    # 创建groups
    groups = [
        (3, nodes1),
        (3, nodes2),
        (9, nodes3),
        (6, nodes4)
    ]

    # 合并groups
    merged_groups = merge_node_group(groups, 5, 100, 3)

    assert len(merged_groups) == 3
    assert [node.node_id for node in merged_groups[0]] == ['node3', 'node1', 'node2']
    assert [node.node_id for node in merged_groups[1]] == ['node4', 'node5']
    assert [node.node_id for node in merged_groups[2]] == ['node6']
