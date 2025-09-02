import pytest

from bella_rag.schema.nodes import TextNode
from bella_rag.utils.cache_util import NodeLRUCache


@pytest.fixture
def cache():
    return NodeLRUCache(capacity=5)


def test_put_and_get(cache):
    cache.put("file1", [TextNode(id_="node1"), TextNode(id_="node2")])
    cache.put("file2", [TextNode(id_="node3"), TextNode(id_="node4")])
    cache.put("file3", [TextNode(id_="node5")])

    assert cache.get("file1", "node1").node_id == "node1"
    assert cache.get("file2", "node3").node_id == "node3"
    assert cache.get("file3", "node5").node_id == "node5"


def test_eviction_policy(cache):
    cache.put("file1", [TextNode(id_="node1"), TextNode(id_="node2")])
    cache.put("file2", [TextNode(id_="node3"), TextNode(id_="node4")])
    cache.put("file3", [TextNode(id_="node5")])

    assert cache.get("file1", "node1").node_id == "node1"
    cache.put("file4", [TextNode(id_="node6")])
    cache.put("file5", [TextNode(id_="node7")])

    cache.put("file6", [TextNode(id_="node8")])
    assert cache.get("file2", "node3") is None
    assert cache.get("file2", "node4") is None

    assert cache.get("file1", "node1").node_id == "node1"


def test_cache_overflow(cache):
    cache.put("file1", [TextNode(id_="node1"), TextNode(id_="node2")])
    cache.put("file2", [TextNode(id_="node3"), TextNode(id_="node4")])
    cache.put("file3", [TextNode(id_="node5")])
    cache.put("file4", [TextNode(id_="node6")])

    assert cache.get("file1", "node1") is None
    cache.put("file5", [TextNode(id_="node7")])

    cache.put("file6", [TextNode(id_="node8")])
    assert cache.get("file1", "node2") is None

    cache.put("file7", [TextNode(id_="node9")])
    assert cache.get("file2", "node3") is None
    assert cache.get("file2", "node4") is None


def test_remove_file(cache):
    cache.put("file1", [TextNode(id_="node1"), TextNode(id_="node2")])
    cache.put("file2", [TextNode(id_="node3"), TextNode(id_="node4")])
    cache.put("file3", [TextNode(id_="node5")])

    cache.remove("file2")
    assert cache.get("file2", "node3") is None
    assert cache.get("file2", "node4") is None

    assert cache.get("file1", "node1").node_id == "node1"
    assert cache.get("file3", "node5").node_id == "node5"
