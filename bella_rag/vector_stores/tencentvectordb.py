import json
from typing import Any, List, Optional

from llama_index.core.vector_stores import VectorStoreQuery, VectorStoreQueryResult
from llama_index.core.vector_stores.utils import DEFAULT_DOC_ID_KEY, DEFAULT_TEXT_KEY
from llama_index.legacy.vector_stores.tencentvectordb import FIELD_VECTOR
from llama_index.vector_stores.tencentvectordb import TencentVectorDB as OriginalTencentVectorDB
from llama_index.vector_stores.tencentvectordb.base import FIELD_ID, FIELD_METADATA, DEFAULT_TIMEOUT
from tcvectordb.model.document import Filter, Document

from common.helper.exception import CheckError
from init.settings import user_logger
from bella_rag.meta.meta_data import NodeTypeEnum
from bella_rag.schema.nodes import TextNode, QaNode, BaseNode, ImageNode, DocumentNodeRelationship
from bella_rag.transformations.index_extend.index_extend_transform_component import IndexExtendTransformComponent
from bella_rag.utils.trace_log_util import trace
from bella_rag.vector_stores.index import FIELD_RELATIONSHIPS, VectorIndex
from bella_rag.vector_stores.types import FilterOperator, MetadataFilters, MetadataFilter
from bella_rag.vector_stores.bella_vector_store import BellaVectorStore

class TencentVectorDB(OriginalTencentVectorDB, BellaVectorStore):
    stores_text: bool

    def __init__(self, stores_text: bool = True, **kwargs: Any):
        self.stores_text = stores_text
        super().__init__(**kwargs)

    """
    llama_index 当前版本对接的腾讯向量库不支持除了eq意外的任何关键字操作，也不支持数组类型需要在这扩展
    现在版本 llama-index-vector-stores-tencentvectordb==0.1.3，如果后续官方支持了就不需要重写方法了
    """

    def version(self):
        return "0.1.3"

    def _init_filter_fields(self) -> None:
        fields = vars(self.collection).get("indexes", [])
        for field in fields:
            if field["fieldName"] not in [FIELD_ID, FIELD_VECTOR]:
                self.filter_fields.append(
                    FilterField(name=field["fieldName"], data_type=field["fieldType"])
                )

    @trace("update_vector_index")
    def update_vector(
            self,
            metadata_filters: MetadataFilters,
            document: Document
    ) -> None:
        """
        更新向量 - 使用统一的MetadataFilters接口
        
        Args:
            metadata_filters: 元数据过滤器，用于指定要更新的向量
            document: 文档对象，包含要更新的数据
        """
        # 将MetadataFilters转换为腾讯向量库Filter
        tencent_filter = self._build_tencent_filter_string(metadata_filters)

        if tencent_filter:
            self.collection.update(data=document, filter=tencent_filter)
        else:
            user_logger.warning("No valid filter provided for update_vector")

    def update_field_by_filter(self, filter_key: str, filter_value: str, field_name: str, field_value: str) -> None:
        """
        根据过滤条件更新指定字段
        
        Args:
            filter_key: 过滤字段名
            filter_value: 过滤值
            field_name: 要更新的字段名
            field_value: 新的字段值
        """
        try:
            from tcvectordb.model.document import Document, Filter

            # 创建更新文档
            doc = Document()
            doc.__dict__[field_name] = field_value

            # 构建过滤条件
            condition = f"{filter_key}=\"{filter_value}\""
            vector_filter = Filter(cond=condition)

            # 执行更新
            self.collection.update(data=doc, filter=vector_filter)

            user_logger.info(f"Updated field {field_name}={field_value} where {filter_key}={filter_value}")

        except Exception as e:
            user_logger.error(f"Failed to update field in TencentVectorDB: {e}")
            raise

    @trace("insert_vector_index")
    def add(
            self,
            nodes: List[BaseNode],
            **add_kwargs: Any,
    ) -> List[str]:
        """Add nodes to index.

        Args:
            nodes: List[BaseNode]: list of nodes with embeddings

        """
        from tcvectordb.model.document import Document

        ids = []
        entries = []
        for node in nodes:
            document = Document(id=node.node_id, vector=node.get_embedding())
            if node.metadata is not None:
                document.__dict__[FIELD_METADATA] = json.dumps(node.metadata)
                for field in self.filter_fields:
                    v = node.metadata.get(field.name)
                    if field.match_value(v):
                        document.__dict__[field.name] = v
            if self.stores_text and isinstance(node, TextNode) and node.text is not None:
                document.__dict__[DEFAULT_TEXT_KEY] = node.text

            entries.append(document)
            ids.append(node.node_id)

            if len(entries) >= self.batch_size:
                self.collection.upsert(
                    documents=entries, build_index=True, timeout=DEFAULT_TIMEOUT
                )
                entries = []

        if len(entries) > 0:
            self.collection.upsert(
                documents=entries, build_index=True, timeout=DEFAULT_TIMEOUT
            )

        return ids

    @trace("delete_file_vector_index")
    def delete(self, ref_doc_id: str, delete_key: str = DEFAULT_DOC_ID_KEY, **delete_kwargs: Any) -> None:
        """
                Delete nodes using with ref_doc_id or ids.

                Args:
                    ref_doc_id (str): The doc_id of the document to delete.
                    delete_key (str): The key of index to delete the document.
                """
        if ref_doc_id is None or len(ref_doc_id) == 0:
            return

        delete_ids = ref_doc_id if isinstance(ref_doc_id, list) else [ref_doc_id]

        # 使用统一的MetadataFilters接口
        metadata_filters = MetadataFilters(
            filters=[
                MetadataFilter(key=delete_key, value=delete_ids, operator=FilterOperator.IN)
            ]
        )

        self.delete_by_filter(metadata_filters)

    @trace("delete_vector_index")
    def delete_documents(self, doc_ids: List[str]) -> None:
        self.collection.delete(document_ids=doc_ids)

    def delete_by_filter(self, metadata_filters: MetadataFilters) -> None:
        """
        通过元数据过滤器删除向量 - 使用统一的MetadataFilters接口
        
        Args:
            metadata_filters: 元数据过滤器，用于指定要删除的向量
        """
        # 将MetadataFilters转换为腾讯向量库Filter
        tencent_filter = self._build_tencent_filter_string(metadata_filters)

        if not tencent_filter:
            user_logger.warning("No valid filter provided for delete_by_filter")
            return

        # 分批删除，向量库一次删除数据量超过16384会直接报错
        delete_batch_limit = 15000
        while True:
            del_res = self.collection.delete(filter=tencent_filter, limit=delete_batch_limit)
            if not del_res or del_res.get('code', -1) != 0:
                user_logger.error(f'delete data from tencent vectordb failed : {del_res}')
                return

            if del_res.get('affectedCount') < delete_batch_limit:
                # 删除完毕
                return

    @trace("vector_query")
    def query(self, query: VectorStoreQuery, index: VectorIndex, index_extend: IndexExtendTransformComponent = None,
              **kwargs: Any) -> VectorStoreQueryResult:
        """Query index for top k most similar nodes.

                Args:
                    query (VectorStoreQuery): contains
                        query_embedding (List[float]): query embedding
                        similarity_top_k (int): top k most similar nodes
                        doc_ids (Optional[List[str]]): filter by doc_id
                        filters (Optional[MetadataFilters]): filter result
                    kwargs.filter (Optional[str|Filter]):

                    if `kwargs` in kwargs:
                       using filter: `age > 20 and author in (...) and ...`
                    elif query.filters:
                       using filter: " and ".join([f'{f.key} = "{f.value}"' for f in query.filters.filters])
                    elif query.doc_ids:
                       using filter: `doc_id in (query.doc_ids)`

                    index : vector store index structure
                    index_extend : vector store index extend storage
                """
        search_filter = self._to_vdb_filter(query, **kwargs)
        if "retrieve_vector" in kwargs:
            retrieve_vector = kwargs.pop("retrieve_vector")
        else:
            retrieve_vector = False
        results = self.collection.search(
            vectors=[query.query_embedding],
            limit=query.similarity_top_k,
            retrieve_vector=retrieve_vector,
            output_fields=query.output_fields,
            filter=search_filter,
            params=SearchParam(ef=10000),
            timeout=60
        )
        if len(results) == 0:
            return VectorStoreQueryResult(nodes=[], similarities=[], ids=[])

        nodes = []
        similarities = []
        ids = []
        for doc in results[0]:
            ids.append(doc.get(FIELD_ID))
            similarities.append(doc.get("score"))
            node = self.doc2node(doc, index)
            nodes.append(node)

        if index_extend is not None:
            nodes = index_extend.batch_set_node_contents(nodes=nodes)

        return VectorStoreQueryResult(nodes=nodes, similarities=similarities, ids=ids)

    @staticmethod
    def _build_tencent_filter_string(filters: MetadataFilters) -> str:
        """
        构建腾讯云向量数据库的过滤条件字符串
        """

        def build_single_filter(filter_obj) -> str:
            """构建单个过滤器的字符串"""
            if isinstance(filter_obj, MetadataFilter):
                if filter_obj.operator.value == FilterOperator.EQ.value:
                    return f'{filter_obj.key} = "{filter_obj.value}"'
                elif filter_obj.operator.value == FilterOperator.ANY.value:
                    return Filter.Include(key=filter_obj.key, value=filter_obj.value)
                elif filter_obj.operator.value == FilterOperator.ALL.value:
                    return Filter.IncludeAll(key=filter_obj.key, value=filter_obj.value)
                elif filter_obj.operator.value == FilterOperator.IN.value:
                    return Filter.In(key=filter_obj.key, value=filter_obj.value)
                elif filter_obj.operator.value == FilterOperator.EXClUDE.value:
                    return Filter.Exclude(key=filter_obj.key, value=[filter_obj.value])
                elif filter_obj.operator.value == FilterOperator.NE.value:
                    return f'{filter_obj.key} != "{filter_obj.value}"'
                else:
                    raise CheckError(f"还未支持的filter方法:{filter_obj.operator.value}")
            elif isinstance(filter_obj, MetadataFilters):
                # 递归处理嵌套的 MetadataFilters
                return build_filters_string(filter_obj)
            else:
                raise CheckError(f"Unsupported filter type: {type(filter_obj)}")

        def build_filters_string(metadata_filters: MetadataFilters) -> str:
            """构建过滤器组的字符串"""
            if not metadata_filters.filters:
                return ""

            # 构建每个过滤器的字符串
            filter_strings = []
            for filter_obj in metadata_filters.filters:
                filter_str = build_single_filter(filter_obj)
                if filter_str:
                    filter_strings.append(filter_str)

            if not filter_strings:
                return ""

            if len(filter_strings) == 1:
                return filter_strings[0]

            # 使用条件连接多个过滤器
            condition = metadata_filters.condition.value if metadata_filters.condition else "and"

            # 如果有多个条件，需要用括号包围
            return f"({f' {condition} '.join(filter_strings)})"

        return build_filters_string(filters)

    @staticmethod
    def _to_vdb_filter(query: VectorStoreQuery, **kwargs: Any) -> Any:
        from tcvectordb.model.document import Filter

        search_filter = None
        if "filter" in kwargs:
            search_filter = kwargs.pop("filter")
            search_filter = (
                search_filter
                if type(search_filter) is Filter
                else Filter(search_filter)
            )
        elif query.filters is not None and len(query.filters.legacy_filters()) > 0:
            search_filter = Filter(TencentVectorDB._build_tencent_filter_string(query.filters))
        elif query.doc_ids is not None:
            search_filter = Filter(Filter.In(DEFAULT_DOC_ID_KEY, query.doc_ids))
        return search_filter

    def query_by_filter(self,
                        limit: Optional[int] = None,
                        offset: Optional[int] = None,
                        document_ids: Optional[List] = None,
                        filter_condition: Optional[Any] = None,  # 支持 Filter 或 MetadataFilters
                        index: Optional[VectorIndex] = None,
                        index_extend: Optional[IndexExtendTransformComponent] = None,
                        **kwargs: Any) -> List[BaseNode]:
        """通过过滤器查询 - 支持 MetadataFilters 和原生 Filter"""
        
        query_filter = filter_condition
        if filter_condition and hasattr(filter_condition, 'filters'):
            # 如果是 MetadataFilters 类型，转换为腾讯向量库 Filter
            from tcvectordb.model.document import Filter
            filter_string = self._build_tencent_filter_string(filter_condition)
            query_filter = Filter(filter_string) if filter_string else None
        
        docs = self.collection.query(filter=query_filter, offset=offset, limit=limit, document_ids=document_ids, **kwargs)
        nodes = []
        for doc in docs:
            node = self.doc2node(doc, index)
            user_logger.info(f'node metadata:{node.metadata}')
            nodes.append(node)

        if index_extend is not None:
            nodes = index_extend.batch_set_node_contents(nodes=nodes)
        return nodes

    def doc2node(self, doc: Document, index: Optional[VectorIndex] = None) -> BaseNode:
        relationships_str = doc.get(FIELD_RELATIONSHIPS)
        relationships = {} if relationships_str is None else json.loads(relationships_str)
        meta_str = doc.get(FIELD_METADATA)
        metadata = {} if meta_str is None else json.loads(meta_str)
        node_type = NodeTypeEnum.TEXT.node_type_code
        metadata[FIELD_RELATIONSHIPS] = relationships
        if index:
            if doc.get(index.doc_id_key):
                metadata[index.doc_id_key] = doc.get(index.doc_id_key)
            if doc.get(index.doc_type_key):
                metadata[index.doc_type_key] = doc.get(index.doc_type_key)
            if doc.get(index.doc_name_key):
                metadata[index.doc_name_key] = doc.get(index.doc_name_key)
            if doc.get(index.extra_key):
                metadata[index.extra_key] = doc.get(index.extra_key)
            if doc.get(index.group_id_key):
                metadata[index.group_id_key] = doc.get(index.group_id_key)
            node_type = index.doc_type or doc.get(index.doc_type_key, NodeTypeEnum.TEXT.node_type_code)

        if node_type == NodeTypeEnum.TEXT.node_type_code:
            if 'context_id' in metadata.keys():
                # 上下文节点包含CONTEXTUAL_GROUP类型的relation
                contextual_relationship = {DocumentNodeRelationship.CONTEXTUAL_GROUP: []}
                node = TextNode(
                    id_=doc.get(FIELD_ID),
                    metadata=metadata,
                    context_id=metadata.get('context_id'),
                    doc_relationships=contextual_relationship,
                    embedding=doc.get(FIELD_VECTOR),
                )
            else:
                node = TextNode(
                    id_=doc.get(FIELD_ID),
                    metadata=metadata,
                    embedding=doc.get(FIELD_VECTOR),
                )
        elif node_type == NodeTypeEnum.QA.node_type_code:
            node = QaNode(
                id_=doc.get(FIELD_ID),
                metadata=metadata,
            )
        elif node_type == NodeTypeEnum.IMAGE.node_type_code:
            node = ImageNode(
                id_=doc.get(FIELD_ID),
                metadata=metadata,
            )
        return node

    async def aquery(self, query: VectorStoreQuery, index: VectorIndex,
                     index_extend: IndexExtendTransformComponent = None,
                     **kwargs: Any) -> VectorStoreQueryResult:
        search_filter = self._to_vdb_filter(query, **kwargs)
        if "retrieve_vector" in kwargs:
            retrieve_vector = kwargs.pop("retrieve_vector")
        else:
            retrieve_vector = True
        results = self.collection.search(
            vectors=[query.query_embedding],
            limit=query.similarity_top_k,
            retrieve_vector=retrieve_vector,
            output_fields=query.output_fields,
            filter=search_filter,
            params=SearchParam(ef=10000)
        )
        if len(results) == 0:
            return VectorStoreQueryResult(nodes=[], similarities=[], ids=[])

        nodes = []
        similarities = []
        ids = []
        for doc in results[0]:
            ids.append(doc.get(FIELD_ID))
            similarities.append(doc.get("score"))
            node = self.doc2node(doc, index)
            nodes.append(node)

        if index_extend is not None:
            nodes = await index_extend.async_batch_set_node_contents(nodes=nodes)

        return VectorStoreQueryResult(nodes=nodes, similarities=similarities, ids=ids)


class FilterField:
    """
    添加支持数组类型的操作
    """
    name: str
    data_type: str = "string"

    def __init__(self, name: str, data_type: str = "string"):
        self.name = name
        self.data_type = "string" if data_type is None else data_type

    def match_value(self, value: Any) -> bool:
        if self.data_type == "uint64":
            return isinstance(value, int)
        elif self.data_type == "array":
            return isinstance(value, List)
        else:
            return isinstance(value, str)

    def to_vdb_filter(self) -> Any:
        from tcvectordb.model.enum import FieldType, IndexType
        from tcvectordb.model.index import FilterIndex

        return FilterIndex(
            name=self.name,
            field_type=FieldType(self.data_type),
            index_type=IndexType.FILTER,
        )


class SearchParam:
    ef: int

    def __init__(self, ef: int):
        self.ef = ef

    @property
    def __dict__(self):
        return {
            "ef": self.ef,
        }
