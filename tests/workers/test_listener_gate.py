import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import patch

# 仅加载 app/workers/listeners/base.py 一个模块，不触发 app.workers 包 __init__。
# 公共仓库中 app.workers 包级导入链会引用仅存在于内部分支的 ke_business，
# 无法在公共仓库整体导入，因此单元测试在隔离模块上验证门控逻辑。
_BASE_PY = (
        Path(__file__).resolve().parent.parent.parent
        / 'app' / 'workers' / 'listeners' / 'base.py'
)


def _load_base_listener():
    """隔离加载 base.py：伪造父包避免执行包级导入链。"""
    for parent in ('app', 'app.workers', 'app.workers.listeners'):
        sys.modules.setdefault(parent, types.ModuleType(parent))
    spec = importlib.util.spec_from_file_location(
        'app.workers.listeners.base',
        _BASE_PY,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules['app.workers.listeners.base'] = module
    spec.loader.exec_module(module)
    return module


_base = _load_base_listener()
BaseListener = _base.BaseListener

# base.py 通过 `from init.settings import KAFKA` 绑定模块级引用，
# 因此必须 patch 隔离加载出的模块对象上的 KAFKA，而不是 init.settings.KAFKA。
def _patch_switch(enabled):
    return patch.object(_base, 'KAFKA', {'VECTOR_INDEX_CONSUME_ENABLED': enabled})


def _complete_task_config():
    return {
        'bootstrap_servers': 'localhost:9092',
        'topic': 'test-topic',
        'group_id': 'test-group',
        'callback': lambda payload: True,
        'callback_timeout': 1,
    }


class _GatedListener(BaseListener):
    consume_switch_key = 'VECTOR_INDEX_CONSUME_ENABLED'


class _GatedListenerWithConfig(_GatedListener):
    def __init__(self, instance_num):
        super().__init__(instance_num, **_complete_task_config())


class _UngatedListener(BaseListener):
    consume_switch_key = None


def test_gated_listener_skipped_when_switch_off():
    with _patch_switch(False):
        listener = _GatedListener(1, **_complete_task_config())
    assert listener._enable is False


def test_gated_listener_created_when_switch_on():
    with _patch_switch(True), patch('common.tool.kafka_tool.Consumer'):
        listener = _GatedListener(1, **_complete_task_config())
    assert listener._enable is True


def test_ungated_listener_ignores_switch():
    with _patch_switch(False), patch('common.tool.kafka_tool.Consumer'):
        listener = _UngatedListener(1, **_complete_task_config())
    assert listener._enable is True


def test_get_instance_skips_gated_when_switch_off():
    with _patch_switch(False):
        assert _GatedListenerWithConfig.get_instance(1) == []
