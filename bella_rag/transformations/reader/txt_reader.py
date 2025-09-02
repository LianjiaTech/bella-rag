from io import IOBase
from typing import List

from bella_rag.schema.document import Document
from bella_rag.transformations.reader import read_all
from bella_rag.transformations.reader.base import BaseReader


class TxtReader(BaseReader):

    def load_data(self, stream: IOBase) -> List[Document]:
        documents = []
        content = read_all(stream).decode("utf-8")
        documents.append(Document(text=content))
        stream.close()
        return documents
