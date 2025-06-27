# coding:utf-8

import os
import configparser
from typing import Dict, Any, Optional, Union


class SafeConfigParser(configparser.ConfigParser):
    """保持配置项大小写敏感的ConfigParser"""
    def __init__(self, defaults=None):
        super().__init__(defaults)

    def optionxform(self, optionstr):
        return optionstr


class ConfigManager:
    """
    配置管理器，支持：
    1. 可选配置项
    2. 环境变量覆盖
    3. 默认值设置
    4. 标准化配置项
    """
    
    def __init__(self, config_file: str, encoding: str = "utf-8"):
        self.config_file = config_file
        self.encoding = encoding
        self._config_dict = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
        
        cf = SafeConfigParser()
        cf.read(self.config_file, encoding=self.encoding)
        
        for section in cf.sections():
            self._config_dict[section] = {}
            for key, value in cf.items(section):
                # 支持环境变量覆盖，格式：SECTION_KEY
                env_key = f"{section.upper()}_{key.upper()}"
                env_value = os.getenv(env_key)
                self._config_dict[section][key] = env_value if env_value is not None else value
    
    def get_section(self, section: str, default: Optional[Dict] = None) -> Dict[str, str]:
        """获取整个配置节，如果不存在返回默认值"""
        return self._config_dict.get(section, default or {})
    
    def get(self, section: str, key: str, default: Any = None, convert_type: type = str) -> Any:
        """获取配置项，支持类型转换和默认值"""
        try:
            value = self._config_dict[section][key]
            if convert_type == bool:
                return value.lower() in ('true', '1', 'yes', 'on')
            elif convert_type == int:
                return int(value)
            elif convert_type == float:
                return float(value)
            elif convert_type == list:
                # 支持逗号分隔的列表
                return [item.strip() for item in value.split(',') if item.strip()]
            else:
                return convert_type(value)
        except (KeyError, ValueError, TypeError):
            return default
    
    def get_required(self, section: str, key: str, convert_type: type = str) -> Any:
        """获取必需的配置项，如果不存在会抛出异常"""
        if section not in self._config_dict or key not in self._config_dict[section]:
            raise ValueError(f"必需的配置项不存在: [{section}].{key}")
        return self.get(section, key, convert_type=convert_type)
    
    def has_section(self, section: str) -> bool:
        """检查配置节是否存在"""
        return section in self._config_dict
    
    def has_option(self, section: str, key: str) -> bool:
        """检查配置项是否存在"""
        return section in self._config_dict and key in self._config_dict[section]
    
    @property
    def config_dict(self) -> Dict[str, Dict[str, str]]:
        """返回完整的配置字典（向后兼容）"""
        return self._config_dict



# 全局配置实例
config_manager: Optional[ConfigManager] = None


def init_config(config_file: str) -> ConfigManager:
    """初始化全局配置管理器"""
    global config_manager
    config_manager = ConfigManager(config_file)
    return config_manager


def get_config() -> ConfigManager:
    """获取全局配置管理器实例"""
    if config_manager is None:
        raise RuntimeError("配置管理器未初始化，请先调用 init_config()")
    return config_manager 