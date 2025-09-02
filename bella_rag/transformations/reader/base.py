from typing import List

from llama_index.core.readers.base import BaseReader as LlamaBaseReader

from bella_rag.config.registry import Registry
from bella_rag.schema.document import Document


class BaseReader(LlamaBaseReader):


    def load_file(self, file_id: str) -> List[Document]:
        file_stream = Registry.get_loader().load_file_stream(file_id)
        file_stream.seek(0)
        return self.load_data(file_stream)
