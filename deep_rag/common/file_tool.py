from typing import Callable, Optional

from common.helper.exception import CheckError
from bella_rag.utils.openapi_util import count_tokens


def chunk_file_content(file_content: str, left_tokens: int):
    # 基于剩下的token数，对文件内容进行进行分组，后续按照分组内容进行提交处理
    file_content_tokens = count_tokens(file_content)
    if file_content_tokens > left_tokens:
        chunks = [file_content[i:i + left_tokens] for i in range(0, len(file_content), left_tokens)]
        return chunks



class FileReader:

    read_func: Optional[Callable[[str], str]] = None

    def __init__(self, read_func: Optional[Callable[[str], str]] = None):
        self.read_func = read_func

    def register_reader(self, read_func: Callable[[str], str]):
        self.read_func = read_func

    def read_file(self, file_id: str) -> str:
        """读取文件内容"""
        if self.read_func is None:
            raise CheckError("找不到读取文件内容的方法!")
        return self.read_func(file_id)
