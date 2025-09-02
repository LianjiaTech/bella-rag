from typing import Union, List

from llama_index.core.vector_stores.utils import DEFAULT_TEXT_KEY, DEFAULT_DOC_ID_KEY

NODE_TYPE = "node_type"
FIELD_RELATIONSHIPS = 'relationships'
EXTRA = "extra"

class BaseIndex:

    @property
    def doc_id_key(self) -> str:
        return DEFAULT_DOC_ID_KEY

    @property
    def text_key(self) -> str:
        return DEFAULT_TEXT_KEY

    @property
    def doc_type_key(self) -> str:
        return NODE_TYPE

    @property
    def relationships_key(self) -> str:
        return FIELD_RELATIONSHIPS

    @property
    def extra_key(self):
        return EXTRA

    @property
    def doc_type(self) -> Union[str, None]:
        return None

    @property
    def group_id_key(self) -> Union[str, None]:
        return None

    def index_keys(self) -> List[str]:
        return [self.doc_id_key, self.text_key, self.doc_type_key, self.relationships_key, self.extra_key]


class VectorIndex(BaseIndex):

    @property
    def vector_key(self) -> Union[str, None]:
        """部分向量库内置该字段"""
        return None