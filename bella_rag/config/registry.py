from typing import Optional

from common.helper.exception import BusinessError
from bella_rag.transformations.reader.file_loader import FileLoader


class Registry:
    """
    全局组件管理器
    支持注册及加载组件
    """

    _instance: Optional['Registry'] = None
    _loader: Optional[FileLoader] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register_loader(cls, loader: FileLoader) -> None:
        instance = cls()
        instance._loader = loader

    @classmethod
    def get_loader(cls) -> FileLoader:
        instance = cls()
        if instance._loader is None:
            raise BusinessError("no file loader registered!")
        return instance._loader