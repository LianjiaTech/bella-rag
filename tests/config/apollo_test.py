import pytest

from app.config.apollo import rag_es_config


def test_rag_es_config():
    # 测试write属性
    assert not rag_es_config.__getattr__("write"), "Expected 'write' to be False"
    # 测试read属性
    assert rag_es_config.__getattr__("read"), "Expected 'read' to be True"
    # 测试other属性并捕获异常
    with pytest.raises(Exception) as excinfo:
        rag_es_config.__getattr__("other")
    assert str(excinfo.value) == "'_RagEsConfig' object has no attribute 'other'"
