import io

import pytest

from app.common.contexts import UserContext
from bella_rag.schema.nodes import TextNode, DocumentNodeRelationship
from bella_rag.transformations.factory import TransformationFactory
from bella_rag.transformations.parser.excel_parser import ExcelParser
from bella_rag.utils.schema_util import build_relation_detect_single_direction_cycles

UserContext.user_id = "mock_user"  # 构建前必须先set user_context

from bella_rag.transformations.parser.pdf_parser import PdfParser
from bella_rag.utils import schema_util


def test_nodes_trans():
    loader = TransformationFactory.get_reader('pdf')
    with open("../resources/测试.pdf", 'rb') as file:
        byte_stream = file.read()
    docs = loader.load_data(io.BytesIO(byte_stream))

    parser = PdfParser()
    domtree = parser._parse_pdf(documents=docs)
    print(domtree)

    nodes = schema_util.dom2nodes(domtree)
    print(nodes)


def test_excel_node_parse():
    loader = TransformationFactory.get_reader('xlsx')
    with open("../resources/测试.xlsx", 'rb') as file:
        byte_stream = file.read()
    docs = loader.load_data(io.BytesIO(byte_stream))
    print(docs)

    parser = ExcelParser()

    def list_to_sequences(lst):
        it = iter(lst)
        while True:
            seq = list(it)
            if not seq:
                break
            yield seq

    nodes = parser._parse_nodes(list_to_sequences(docs))
    print(nodes)


@pytest.fixture
def setup_nodes():
    # 创建测试数据
    node_map = {
        'node1': TextNode(id_='node1'),
        'node2': TextNode(id_='node2'),
        'node3': TextNode(id_='node3'),
        'node4': TextNode(id_='node4'),
        'node5': TextNode(id_='node5'),
        'node6': TextNode(id_='node6'),
        'node7': TextNode(id_='node7')
    }
    node_relation_map = {
        'node1': {'right': 'node2'},
        'node2': {'left': 'node1', 'right': 'node3'},
        'node3': {'left': 'node2', 'right': 'node4'},
        'node4': {'left': 'node3'},
        'node5': {'parent': 'node1', 'child': ['node6', 'node7']},
        'node6': {'parent': 'node5'},
        'node7': {'parent': 'node5'}
    }
    return node_map, node_relation_map


def test_no_cycle(setup_nodes):
    node_map, node_relation_map = setup_nodes
    visited = set()
    result = build_relation_detect_single_direction_cycles('node1', node_map, node_relation_map, visited)
    assert not result
    assert node_map['node1'].doc_relationships[DocumentNodeRelationship.RIGHT] == node_map['node2']
    assert node_map['node2'].doc_relationships[DocumentNodeRelationship.LEFT] == node_map['node1']
    assert node_map['node2'].doc_relationships[DocumentNodeRelationship.RIGHT] == node_map['node3']
    assert node_map['node3'].doc_relationships[DocumentNodeRelationship.LEFT] == node_map['node2']
    assert node_map['node3'].doc_relationships[DocumentNodeRelationship.RIGHT] == node_map['node4']
    assert node_map['node4'].doc_relationships[DocumentNodeRelationship.LEFT] == node_map['node3']


def test_with_cycle(setup_nodes):
    node_map, node_relation_map = setup_nodes
    node_relation_map['node4']['right'] = 'node1'  # 添加闭环

    visited = set()
    result = build_relation_detect_single_direction_cycles('node1', node_map, node_relation_map, visited)
    assert not result
    assert node_map['node1'].doc_relationships[DocumentNodeRelationship.RIGHT] == node_map['node2']
    assert node_map['node2'].doc_relationships[DocumentNodeRelationship.LEFT] == node_map['node1']
    assert node_map['node2'].doc_relationships[DocumentNodeRelationship.RIGHT] == node_map['node3']
    assert node_map['node3'].doc_relationships[DocumentNodeRelationship.LEFT] == node_map['node2']
    assert node_map['node3'].doc_relationships[DocumentNodeRelationship.RIGHT] == node_map['node4']
    assert node_map['node4'].doc_relationships[DocumentNodeRelationship.LEFT] == node_map['node3']
    assert DocumentNodeRelationship.RIGHT not in node_map['node4'].doc_relationships


def test_children_with_one_cycle(setup_nodes):
    node_map, node_relation_map = setup_nodes
    node_relation_map['node5']['child'] = ['node6', 'node7']
    node_relation_map['node7']['child'] = ['node5']  # 添加父子闭环

    visited = set()
    result = build_relation_detect_single_direction_cycles('node5', node_map, node_relation_map, visited)
    assert not result
    assert node_map['node5'].doc_relationships[DocumentNodeRelationship.PARENT] == node_map['node1']
    assert node_map['node5'].doc_relationships[DocumentNodeRelationship.CHILD] == [node_map['node6'], node_map['node7']]
    assert node_map['node6'].doc_relationships[DocumentNodeRelationship.PARENT] == node_map['node5']
    assert node_map['node7'].doc_relationships[DocumentNodeRelationship.PARENT] == node_map['node5']
    assert DocumentNodeRelationship.CHILD not in node_map['node7'].doc_relationships


def test_previous_next_cycle(setup_nodes):
    node_map, node_relation_map = setup_nodes
    node_relation_map['node4'] = {'next': 'node1'}
    node_relation_map['node1'] = {'next': 'node2'}
    node_relation_map['node2'] = {'next': 'node3'}
    node_relation_map['node3'] = {'next': 'node4'}  # 添加前后闭环

    visited = set()
    result = build_relation_detect_single_direction_cycles('node1', node_map, node_relation_map, visited)
    assert not result
    assert DocumentNodeRelationship.NEXT not in node_map['node4'].doc_relationships


def test_complex_cycle(setup_nodes):
    """
    目前还未支持复杂闭环的检测
    """
    node_map, node_relation_map = setup_nodes
    node_relation_map['node1']['child'] = ['node2']
    node_relation_map['node2']['parent'] = 'node1'
    node_relation_map['node2']['next'] = 'node3'
    node_relation_map['node3']['previous'] = 'node2'
    node_relation_map['node3']['child'] = ['node4']
    node_relation_map['node4']['parent'] = 'node3'
    node_relation_map['node4']['next'] = 'node1'  # 添加复杂闭环

    visited = set()
    result = build_relation_detect_single_direction_cycles('node1', node_map, node_relation_map, visited)
    assert not result
    assert DocumentNodeRelationship.NEXT in node_map['node4'].doc_relationships
    # 无法检测出复杂闭环，node4的next还是node1
    assert node_map['node4'].doc_relationships.get(DocumentNodeRelationship.NEXT) == node_map['node1']
