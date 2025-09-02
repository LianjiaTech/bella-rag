from io import IOBase
from typing import List, Optional

from fitz import fitz

from init.settings import user_logger
from bella_rag.schema.document import Document
from bella_rag.transformations.reader.base import BaseReader


class PdfReader(BaseReader):

    def load_data(self, stream: IOBase) -> List[Document]:
        try:
            # 读取整个文件内容为bytes
            bytes_stream = stream.read()
            stream.close()
            if not isinstance(bytes_stream, bytes):
                raise ValueError("Stream did not return bytes")

            document = Document(stream=bytes_stream, text=self.load_pdf_text(bytes_stream))
            return [document]
        except Exception as e:
            user_logger.error(f"Error reading PDF: {e}")
            return []

    def load_pdf_text(self, stream: Optional[bytes]):
        doc = fitz.open(stream=stream, filetype="pdf")
        text = ""
        for page_num in range(len(doc)):
            # 获取每一页
            page = doc[page_num]
            # 提取文本
            text = text + page.get_text()
            # 打印文本
        return text
