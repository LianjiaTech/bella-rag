from io import IOBase
from typing import List

from bella_rag.schema.document import Document
from bella_rag.transformations.reader import read_all
from bella_rag.transformations.reader.base import BaseReader


class HtmlReader(BaseReader):

    def load_data(self, stream: IOBase) -> List[Document]:
        text = read_all(stream).decode("utf-8")
        stream.close()
        # html文件整页读取document
        doc = Document(text=text)
        return [doc]