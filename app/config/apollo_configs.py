import json

from common.tool.apollo import get_apollo_config


class _RetrievalConfig(object):
    """
    检索默认策略配置
    """
    def __init__(self):
        self._retrieval_config_key = "retrieval.default.config"

    def _load_retrieval_config(self):
        return json.loads(get_apollo_config(self._retrieval_config_key, "{}"))

    def __getattr__(self):
        return self._load_retrieval_config()

    def get_plugins(self):
        return self.__getattr__().get('plugins', [])

    def get_retrieve_mode(self):
        return self.__getattr__().get('retrieve_mode', 'semantic')


class _FileAccessConfig(object):
    """文件准入条件配置"""
    def __init__(self):
        self._file_access_config_key = "file.access.config"

    def _load_file_access_config(self):
        return json.loads(get_apollo_config(self._file_access_config_key, "{}"))

    def __getattr__(self):
        return self._load_file_access_config()

    def enable_max_node_size(self):
        return self.__getattr__().get('enable_max_node_size', 50000)

    def file_space_black_list(self):
        return self.__getattr__().get('file_space_black_list', [])

    def enable_ak_codes(self):
        # 文件解析准入的ak_code
        return self.__getattr__().get('enable_ak_codes', [])

    def enable_ak_code_filter(self):
        # 开启ak_code白名单准入
        return self.__getattr__().get('enable_ak_code_filter', False)


class _RateLimitConfig(object):
    """
    限流策略
    """
    def __init__(self):
        self._rate_limit_key = "rag.rate.limit"

    def rate_limit_config(self):
        return json.loads(get_apollo_config(self._rate_limit_key, "{}"))



retrieval_default_config = _RetrievalConfig()
file_access_config = _FileAccessConfig()
rate_limit_config = _RateLimitConfig()