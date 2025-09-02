from typing import Union, List

from bella_rag.meta.meta_data import NodeTypeEnum
from bella_rag.vector_stores.index import BaseIndex, VectorIndex


class ChunkVectorIndex(VectorIndex):

    @property
    def doc_id_key(self) -> str:
        return "source_id"

    @property
    def text_key(self) -> str:
        return ""

    @property
    def doc_type_key(self) -> str:
        return "node_type"

    @property
    def doc_name_key(self) -> str:
        return "source_name"

    @property
    def relationships_key(self) -> str:
        return "relationships"

    def index_keys(self) -> List[str]:
        return [self.doc_id_key, self.doc_type_key, self.relationships_key, self.extra_key, self.doc_name_key]


class EsIndex(BaseIndex):

    @property
    def doc_id_key(self) -> str:
        return "source_id"

    @property
    def text_key(self) -> str:
        return "content"

    @property
    def doc_type_key(self) -> str:
        return "type"

    @property
    def doc_name_key(self) -> str:
        return "source_name"

    @property
    def relationships_key(self) -> str:
        return "relationships"

    def index_keys(self) -> List[str]:
        return [self.doc_id_key, self.text_key, self.relationships_key, self.extra_key,
                self.doc_name_key, self.doc_type_key]


class QuestionVectorIndex(VectorIndex):

    @property
    def doc_id_key(self) -> str:
        return "source_id"

    @property
    def doc_type(self) -> Union[str, None]:
        return NodeTypeEnum.QA.node_type_code

    @property
    def doc_name_key(self) -> str:
        return "source_name"

    @property
    def group_id_key(self) -> str:
        return "group_id"

    def index_keys(self) -> List[str]:
        return [self.doc_id_key, self.extra_key, self.group_id_key, self.doc_name_key]
