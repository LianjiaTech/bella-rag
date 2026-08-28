import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class FileApiTaskConfigTest(unittest.TestCase):
    def _load_file_api_task(self, file_api_config):
        class FileIndexingProcessor:
            pass

        class FileSummaryProcessor:
            pass

        stub_modules = {
            "app": self._package("app"),
            "app.config": self._package("app.config"),
            "app.config.apollo_configs": self._module(
                "app.config.apollo_configs", file_access_config=Mock()
            ),
            "app.postprocessors": self._package("app.postprocessors"),
            "app.postprocessors.file_postprocessors": self._module(
                "app.postprocessors.file_postprocessors",
                FileIndexingProcessor=FileIndexingProcessor,
                FileSummaryProcessor=FileSummaryProcessor,
            ),
            "app.services": self._package("app.services"),
            "app.services.file_service": self._module(
                "app.services.file_service", file_delete_submit_task=Mock()
            ),
            "bella_rag": self._package("bella_rag"),
            "bella_rag.utils": self._package("bella_rag.utils"),
            "bella_rag.utils.openapi_util": self._module(
                "bella_rag.utils.openapi_util", _fetch_ak_info=Mock()
            ),
            "bella_rag.utils.file_api_tool": self._module(
                "bella_rag.utils.file_api_tool", file_api_client=Mock()
            ),
            "common": self._package("common"),
            "common.helper": self._package("common.helper"),
            "common.helper.exception": self._module(
                "common.helper.exception", FileNotFoundException=RuntimeError
            ),
            "init": self._package("init"),
            "init.settings": self._module(
                "init.settings",
                FILE_API=file_api_config,
                user_logger=Mock(),
            ),
        }

        module_path = (
            Path(__file__).resolve().parents[2]
            / "app/workers/handlers/file_api_task.py"
        )
        module_name = f"file_api_task_under_test_{id(file_api_config)}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, stub_modules):
            spec.loader.exec_module(module)
        return module, FileIndexingProcessor, FileSummaryProcessor

    @staticmethod
    def _module(name, **attributes):
        module = types.ModuleType(name)
        for key, value in attributes.items():
            setattr(module, key, value)
        return module

    @classmethod
    def _package(cls, name):
        module = cls._module(name)
        module.__path__ = []
        return module

    def test_summary_processor_is_disabled_by_explicit_configuration(self):
        module, indexing_processor, _ = self._load_file_api_task(
            {"enable_summary": False}
        )

        self.assertEqual(1, len(module.file_api_postprocessors))
        self.assertIsInstance(module.file_api_postprocessors[0], indexing_processor)

    def test_summary_processor_is_enabled_by_startup_configuration(self):
        module, indexing_processor, summary_processor = self._load_file_api_task(
            {"enable_summary": True}
        )

        self.assertEqual(2, len(module.file_api_postprocessors))
        self.assertIsInstance(module.file_api_postprocessors[0], indexing_processor)
        self.assertIsInstance(module.file_api_postprocessors[1], summary_processor)

    def test_summary_processor_is_enabled_when_configuration_is_absent(self):
        module, indexing_processor, summary_processor = self._load_file_api_task({})

        self.assertEqual(2, len(module.file_api_postprocessors))
        self.assertIsInstance(module.file_api_postprocessors[0], indexing_processor)
        self.assertIsInstance(module.file_api_postprocessors[1], summary_processor)


if __name__ == "__main__":
    unittest.main()
