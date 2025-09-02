from abc import abstractmethod
from typing import IO, Optional

from bella_rag.llm.openapi import FileAPIClient


class FileLoader:
    """文件流加载器"""

    @abstractmethod
    def load_file_stream(self, file_id: str) -> IO:
        """通过file id加载文件流"""


class FileApiLoader(FileLoader):

    client: Optional[FileAPIClient] = None

    def __init__(self, client: Optional[FileAPIClient] = None):
        self.client = client

    def load_file_stream(self, file_id: str) -> IO:
        return self.client.file_content(file_id)
