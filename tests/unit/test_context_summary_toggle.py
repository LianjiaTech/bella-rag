import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from common.tool.config_manager import ConfigManager


ROOT = Path(__file__).resolve().parents[2]


def module(name, **attributes):
    result = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(result, key, value)
    return result


def package(name):
    result = module(name)
    result.__path__ = []
    return result


class ContextSummaryToggleTest(unittest.TestCase):
    def load_handler(self, config):
        extractor = Mock()
        extractor.type.return_value = 'context_extractor'
        lock = Mock()
        lock.locked.return_value = True
        redis_client = Mock()
        context = type('Context', (), {})
        trace = type('Trace', (), {})
        stubs = {
            'redis': module('redis', Redis=redis_client),
            'redis_lock': module('redis_lock', Lock=Mock(return_value=lock)),
            'app': package('app'),
            'app.common': package('app.common'),
            'app.common.contexts': module('app.common.contexts', UserContext=context, TraceContext=trace),
            'init': package('init'),
            'init.settings': module('init.settings', CONTEXT_SUMMARY=config, user_logger=Mock()),
            'common.tool.redis_tool': module('common.tool.redis_tool', redis_pool=object()),
            'bella_rag': package('bella_rag'),
            'bella_rag.transformations': package('bella_rag.transformations'),
            'bella_rag.transformations.extractor': package('bella_rag.transformations.extractor'),
            'bella_rag.transformations.extractor.extractors': module(
                'bella_rag.transformations.extractor.extractors', ContextExtractor=Mock(return_value=extractor)
            ),
        }
        path = ROOT / 'app/workers/handlers/knowledge_context_summary_task.py'
        spec = importlib.util.spec_from_file_location('context_summary_handler_under_test', path)
        handler = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, stubs):
            spec.loader.exec_module(handler)
        return handler, extractor, stubs['redis_lock'].Lock, redis_client, lock

    def test_disabled_message_is_acknowledged_without_side_effects(self):
        handler, extractor, lock_factory, redis_client, _ = self.load_handler({'ENABLE': False})
        payload = {'file_id': 'file-1', 'extractors': ['context_extractor']}

        self.assertTrue(handler.knowledge_file_context_summary_callback(payload))
        extractor.type.assert_not_called()
        extractor.extract.assert_not_called()
        lock_factory.assert_not_called()
        redis_client.assert_not_called()

    def test_enabled_message_runs_extractor(self):
        handler, extractor, lock_factory, _, lock = self.load_handler({'ENABLE': True})
        payload = {'file_id': 'file-1', 'extractors': ['context_extractor']}

        self.assertTrue(handler.knowledge_file_context_summary_callback(payload))
        extractor.extract.assert_called_once_with(source_id='file-1')
        lock_factory.assert_called_once()
        lock.release.assert_called_once()

    def test_missing_switch_preserves_enabled_behavior(self):
        handler, extractor, _, _, _ = self.load_handler({})

        self.assertTrue(handler.knowledge_file_context_summary_callback(
            {'file_id': 'file-1', 'extractors': ['context_extractor']}
        ))
        extractor.extract.assert_called_once_with(source_id='file-1')

    def test_other_extractors_remain_skipped(self):
        handler, extractor, lock_factory, _, _ = self.load_handler({'ENABLE': True})

        self.assertTrue(handler.knowledge_file_context_summary_callback(
            {'file_id': 'file-1', 'extractors': ['summary_extractor']}
        ))
        extractor.extract.assert_not_called()
        lock_factory.assert_not_called()

    def test_environment_variable_overrides_ini_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'settings.ini'
            path.write_text('[CONTEXT_SUMMARY]\nenable = True\n')
            with patch.dict(os.environ, {'CONTEXT_SUMMARY_ENABLE': 'false'}):
                config = ConfigManager(str(path))
                self.assertFalse(config.get('CONTEXT_SUMMARY', 'enable', True, bool))


if __name__ == '__main__':
    unittest.main()
