import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[2]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ApiCallModesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.modes = load_module(
            'api_call_mode_under_test',
            ROOT / 'bella_rag/llm/api_call_mode.py',
        )

    def test_direct_mode_preserves_call_headers_without_transfer_headers(self):
        headers = self.modes.build_api_call_headers(
            call_mode=self.modes.DIRECT_CALL_MODE,
            service_client='service-a',
            effective_api_key_code='ak-code',
            extra_headers={'X-Request': 'request-id'},
        )

        self.assertEqual({'X-Request': 'request-id'}, headers)

    def test_billing_transfer_mode_adds_both_transfer_headers(self):
        headers = self.modes.build_api_call_headers(
            call_mode=self.modes.BILLING_TRANSFER_MODE,
            service_client='service-a',
            effective_api_key_code='ak-code',
        )

        self.assertEqual('service-a', headers[self.modes.SERVICE_CLIENT_HEADER])
        self.assertEqual('ak-code', headers[self.modes.EFFECTIVE_API_KEY_CODE_HEADER])

    def test_billing_transfer_mode_requires_service_and_effective_key(self):
        with self.assertRaisesRegex(ValueError, 'service_client'):
            self.modes.build_api_call_headers(
                call_mode=self.modes.BILLING_TRANSFER_MODE,
                effective_api_key_code='ak-code',
            )

        with self.assertRaisesRegex(ValueError, 'usage_ak_code'):
            self.modes.build_api_call_headers(
                call_mode=self.modes.BILLING_TRANSFER_MODE,
                service_client='service-a',
            )

    def test_file_index_embedding_is_configured_for_billing_transfer(self):
        captured = []

        class OpenAPIEmbedding:
            def __init__(self, **kwargs):
                captured.append(kwargs)

        stubs = {
            'app': self._package('app'),
            'app.schema': self._package('app.schema'),
            'app.schema.index': self._module(
                'app.schema.index',
                ChunkVectorIndex=Mock,
                QuestionVectorIndex=Mock,
                EsIndex=Mock,
            ),
            'init': self._package('init'),
            'init.settings': self._module(
                'init.settings',
                OPENAPI={
                    'AK': 'direct-key',
                    'BILLING_TRANSFER_API_KEY': 'transfer-key',
                    'BILLING_TRANSFER_SERVICE_CLIENT': 'service-a',
                },
                VECTOR_DB_COMMON={
                    'EMBEDDING_MODEL': 'embedding-model',
                    'EMBEDDING_BATCH_SIZE': 10,
                    'DIMENSION': 1024,
                },
                RETRIEVAL={'EMBEDDING_TIMEOUT': 5.0},
            ),
            'bella_rag': self._package('bella_rag'),
            'bella_rag.llm': self._package('bella_rag.llm'),
            'bella_rag.llm.api_call_mode': self._module(
                'bella_rag.llm.api_call_mode',
                BILLING_TRANSFER_MODE=self.modes.BILLING_TRANSFER_MODE,
            ),
            'bella_rag.llm.openapi': self._module(
                'bella_rag.llm.openapi', OpenAPIEmbedding=OpenAPIEmbedding
            ),
        }
        path = ROOT / 'app/services/__init__.py'
        with patch.dict(sys.modules, stubs):
            load_module('app_services_under_test', path)

        self.assertEqual(2, len(captured))
        self.assertEqual('transfer-key', captured[0]['api_key'])
        self.assertEqual(self.modes.BILLING_TRANSFER_MODE, captured[0]['call_mode'])
        self.assertEqual('service-a', captured[0]['service_client'])
        self.assertEqual('direct-key', captured[1]['api_key'])
        self.assertNotIn('call_mode', captured[1])
        self.assertNotIn('service_client', captured[1])

    @staticmethod
    def _module(name, **attributes):
        result = types.ModuleType(name)
        for key, value in attributes.items():
            setattr(result, key, value)
        return result

    @classmethod
    def _package(cls, name):
        result = cls._module(name)
        result.__path__ = []
        return result


if __name__ == '__main__':
    unittest.main()
