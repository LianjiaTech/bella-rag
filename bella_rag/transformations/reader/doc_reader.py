from io import IOBase
from typing import List

from llama_index.core import Document

from bella_rag.transformations.reader.base import BaseReader
from bella_rag.utils import doc2text_util


class DocReader(BaseReader):
    """
    doc reader读取文件流文本
    """

    def load_data(self, stream: IOBase) -> List[Document]:
        documents = []
        content = doc2text_util.convert_doc_to_text(stream.read())
        documents.append(Document(text=content))
        stream.close()
        return documents


class DocxReader(BaseReader):
    """
    docx reader读取文件流文本
    """

    def load_data(self, stream: IOBase) -> List[Document]:
        documents = []
        content = doc2text_util.convert_docx_to_text(stream.read())
        documents.append(Document(text=content))
        stream.close()
        return documents
