import json
import uuid
from typing import Any, List, Optional

from llama_index.core.vector_stores import VectorStoreQuery, VectorStoreQueryResult
from llama_index.core.vector_stores.utils import DEFAULT_DOC_ID_KEY
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance, PointStruct,
    Filter, FieldCondition, MatchValue, MatchAny, MatchExcept
)

from bella_rag.utils.trace_log_util import trace

# Qdrant命名空间UUID，用于生成确定性的UUID
QDRANT_NAMESPACE = uuid.UUID('12345678-1234-5678-1234-123456789abc')


def string_to_uuid(text: str) -> str:
    """将字符串转换为UUID格式，用作Qdrant的point ID"""
    return str(uuid.uuid5(QDRANT_NAMESPACE, text))


from init.settings import user_logger
from bella_rag.meta.meta_data import NodeTypeEnum
from bella_rag.schema.nodes import TextNode, QaNode, BaseNode, ImageNode, DocumentNodeRelationship
from bella_rag.transformations.index_extend.index_extend_transform_component import IndexExtendTransformComponent
from bella_rag.vector_stores.index import FIELD_RELATIONSHIPS, VectorIndex
from bella_rag.vector_stores.types import FilterOperator, MetadataFilters, MetadataFilter
from bella_rag.vector_stores.bella_vector_store import BellaVectorStore


class QdrantVectorDB(QdrantVectorStore, BellaVectorStore):
    """
    Qdrant向量数据库客户端
    """

    def __init__(
            self,
            collection_name: str,
            stores_text: bool = True,
            url: Optional[str] = None,
            host: Optional[str] = "localhost",
            port: Optional[int] = 6333,
            grpc_port: Optional[int] = 6334,
            prefer_grpc: bool = False,
            https: Optional[bool] = None,
            api_key: Optional[str] = None,
            prefix: Optional[str] = None,
            timeout: Optional[float] = None,
            path: Optional[str] = None,
            force_disable_check_same_thread: bool = True,
            batch_size: int = 100,
            vector_size: int = 1024,
            distance: Distance = Distance.COSINE,
            **kwargs: Any,
    ):
        """
        初始化Qdrant客户端
        """

        # 初始化Qdrant客户端
        if url:
            client = QdrantClient(
                url=url,
                api_key=api_key,
                timeout=timeout,
                https=https,
            )
        elif path:
            client = QdrantClient(
                path=path,
                force_disable_check_same_thread=force_disable_check_same_thread,
            )
        else:
            client = QdrantClient(
                host=host,
                port=port,
                grpc_port=grpc_port,
                prefer_grpc=prefer_grpc,
                https=https,
                api_key=api_key,
                timeout=timeout,
            )

        from init.settings import user_logger

        super().__init__(
            collection_name=collection_name,
            client=client,
            stores_text=stores_text,
            **kwargs
        )

        object.__setattr__(self, 'batch_size', batch_size)
        object.__setattr__(self, 'vector_size', vector_size)
        object.__setattr__(self, 'distance', distance)
        object.__setattr__(self, '_collection_initialized', False)

        user_logger.info(f"Initialized QdrantVectorDB for collection: {self.collection_name}")

    @property
    def client(self):
        """获取Qdrant客户端实例"""
        return self._client

    @trace("insert_vector_index")
    def add(
            self,
            nodes: List[BaseNode],
            **add_kwargs: Any,
    ) -> List[str]:
        """
        添加节点到索引
        
        Args:
            nodes: 节点列表
            
        Returns:
            节点ID列表
        """
        ids = []
        points = []

        for node in nodes:
            payload = node.metadata.copy() if node.metadata else {}

            # 在payload中保存原始node_id，用于后续查询
            payload['original_node_id'] = node.node_id

            # 生成UUID格式的point ID
            point_id = string_to_uuid(node.node_id)

            # 构建点结构
            point = PointStruct(
                id=point_id,
                vector=node.get_embedding(),
                payload=payload
            )
            points.append(point)
            ids.append(node.node_id)  # 返回原始ID

            # 批量插入
            if len(points) >= self.batch_size:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                points = []

        # 插入剩余的点
        if points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

        return ids

    def _metadata_filters_to_qdrant_filter(self, metadata_filters: MetadataFilters) -> Optional[Filter]:
        """将MetadataFilters转换为Qdrant Filter对象"""
        if not metadata_filters or not metadata_filters.filters:
            return None

        conditions = []

        for filter_obj in metadata_filters.filters:
            if isinstance(filter_obj, MetadataFilter):
                condition = self._build_single_filter(filter_obj)
                if condition:
                    conditions.append(condition)
            elif isinstance(filter_obj, MetadataFilters):
                # 递归处理嵌套的过滤器
                nested_filter = self._metadata_filters_to_qdrant_filter(filter_obj)
                if nested_filter:
                    conditions.extend(nested_filter.must or [])

        if not conditions:
            return None

        return Filter(must=conditions)

    @trace("update_vector_index")
    def update_vector(
            self,
            metadata_filters: MetadataFilters,
            document: Any
    ) -> None:
        """
        更新向量 - 使用统一的MetadataFilters接口
        
        Args:
            metadata_filters: 元数据过滤器，用于指定要更新的向量
            document: 文档对象，包含要更新的数据
        """
        try:
            # 构建更新的payload
            payload = {}

            # 从document.__dict__中提取数据（兼容rename_file的使用方式）
            if hasattr(document, '__dict__'):
                payload.update(document.__dict__)

            # 从document中提取其他数据
            if hasattr(document, 'extra') and document.extra:
                payload['extra'] = document.extra
            if hasattr(document, 'text') and document.text:
                payload['text'] = document.text
            if hasattr(document, 'metadata') and document.metadata:
                payload.update(document.metadata)

            # 移除不需要的字段
            payload.pop('doc_id', None)
            payload.pop('id_', None)

            # 如果没有有效的更新数据，直接返回
            if not payload:
                user_logger.warning("No valid data to update in document")
                return

            # 将MetadataFilters转换为Qdrant Filter
            qdrant_filter = self._metadata_filters_to_qdrant_filter(metadata_filters)

            # 由于Qdrant不支持基于filter的批量更新，我们需要先查询再更新
            user_logger.info(f"Updating vectors with filter: {qdrant_filter}")
            user_logger.info(f"Update payload: {payload}")

            # 先查询匹配的点
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=qdrant_filter,
                limit=1000,  # 批量更新，一次处理1000个
                with_payload=False,  # 只需要ID
                with_vectors=False
            )

            points_to_update = scroll_result[0]
            if not points_to_update:
                user_logger.warning(f"No points found to update with filter: {metadata_filters}")
                return

            user_logger.info(f"Found {len(points_to_update)} points to update")

            # 批量更新点的payload
            update_points = []
            for point in points_to_update:
                # 获取现有的payload
                existing_point = self.client.retrieve(
                    collection_name=self.collection_name,
                    ids=[point.id],
                    with_payload=True,
                    with_vectors=False
                )[0]

                # 合并更新的payload
                updated_payload = existing_point.payload.copy() if existing_point.payload else {}
                updated_payload.update(payload)

                # 创建更新的点结构
                from qdrant_client.http.models import PointStruct
                update_points.append(PointStruct(
                    id=point.id,
                    payload=updated_payload
                ))

                # 批量处理
                if len(update_points) >= self.batch_size:
                    self.client.upsert(
                        collection_name=self.collection_name,
                        points=update_points
                    )
                    update_points = []

            # 处理剩余的点
            if update_points:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=update_points
                )

            user_logger.info(f"Successfully updated {len(points_to_update)} vectors")

        except Exception as e:
            user_logger.error(f"Failed to update vector: {e}")
            raise

    def update_field_by_filter(self, filter_key: str, filter_value: str, field_name: str, field_value: str) -> None:
        """
        根据过滤条件更新指定字段 - 简化版本，专门用于简单的字段更新
        
        Args:
            filter_key: 过滤字段名
            filter_value: 过滤值
            field_name: 要更新的字段名
            field_value: 新的字段值
        """
        try:
            # 构建 MetadataFilters
            metadata_filters = MetadataFilters(
                filters=[
                    MetadataFilter(key=filter_key, value=filter_value, operator=FilterOperator.EQ)
                ]
            )

            # 创建更新文档
            from llama_index.core import Document
            doc = Document()
            doc.__dict__[field_name] = field_value

            # 调用通用的 update_vector 方法
            self.update_vector(metadata_filters, doc)

            user_logger.info(f"Updated field {field_name}={field_value} where {filter_key}={filter_value}")

        except Exception as e:
            user_logger.error(f"Failed to update field: {e}")
            raise

    @trace("delete_file_vector_index")
    def delete(self, ref_doc_id: str, delete_key: str = DEFAULT_DOC_ID_KEY, **delete_kwargs: Any) -> None:
        """
        删除文档
        
        Args:
            ref_doc_id: 文档ID
            delete_key: 删除字段键
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
        """删除文档列表"""
        # 将原始ID转换为UUID格式
        uuid_ids = [string_to_uuid(doc_id) for doc_id in doc_ids]
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=uuid_ids
        )

    def delete_by_filter(self, metadata_filters: MetadataFilters) -> None:
        """
        通过元数据过滤器删除向量 - 使用统一的MetadataFilters接口
        
        Args:
            metadata_filters: 元数据过滤器，用于指定要删除的向量
        """
        # 将MetadataFilters转换为Qdrant Filter
        qdrant_filter = self._metadata_filters_to_qdrant_filter(metadata_filters)

        if qdrant_filter:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=qdrant_filter
            )
        else:
            user_logger.warning("No valid filter provided for delete_by_filter")

    @trace("vector_query")
    def query(
            self,
            query: VectorStoreQuery,
            index: VectorIndex,
            index_extend: IndexExtendTransformComponent = None,
            **kwargs: Any
    ) -> VectorStoreQueryResult:
        """
        查询向量
        
        Args:
            query: 查询对象
            index: 向量索引结构
            index_extend: 索引扩展组件
            
        Returns:
            查询结果
        """
        # 构建过滤器
        query_filter = self._build_query_filter(query, **kwargs)

        # 执行搜索
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query.query_embedding,
            query_filter=query_filter,
            limit=query.similarity_top_k,
            with_payload=True,
            with_vectors=kwargs.get("retrieve_vector", False)
        )

        if not search_result:
            return VectorStoreQueryResult(nodes=[], similarities=[], ids=[])

        # 转换结果
        nodes = []
        similarities = []
        ids = []

        for i, scored_point in enumerate(search_result):
            # 使用原始node_id而不是UUID
            original_node_id = scored_point.payload.get('original_node_id', str(scored_point.id))
            ids.append(original_node_id)
            similarities.append(scored_point.score)
            node = self._point_to_node(scored_point, index)
            nodes.append(node)

        # 使用索引扩展组件设置节点内容
        if index_extend is not None:
            nodes = index_extend.batch_set_node_contents(nodes=nodes)

        return VectorStoreQueryResult(nodes=nodes, similarities=similarities, ids=ids)

    def _build_query_filter(self, query: VectorStoreQuery, **kwargs: Any) -> Optional[Filter]:
        """构建查询过滤器"""
        conditions = []

        # 处理文档ID过滤
        if query.doc_ids:
            if len(query.doc_ids) == 1:
                conditions.append(
                    FieldCondition(
                        key="source_id",
                        match=MatchValue(value=query.doc_ids[0])
                    )
                )
            else:
                conditions.append(
                    FieldCondition(
                        key="source_id",
                        match=MatchAny(any=query.doc_ids)
                    )
                )

        # 处理元数据过滤器
        if query.filters:
            filter_conditions = self._build_metadata_filters(query.filters)
            conditions.extend(filter_conditions)

        # 处理额外的过滤器
        if "filter" in kwargs:
            custom_filter = kwargs["filter"]
            if isinstance(custom_filter, Filter):
                return custom_filter
            elif isinstance(custom_filter, dict):
                for key, value in custom_filter.items():
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )

        if not conditions:
            return None

        return Filter(must=conditions)

    def _build_metadata_filters(self, metadata_filters: MetadataFilters) -> List[FieldCondition]:
        """构建元数据过滤器"""
        conditions = []

        for filter_obj in metadata_filters.filters:
            if isinstance(filter_obj, MetadataFilter):
                condition = self._build_single_filter(filter_obj)
                if condition:
                    conditions.append(condition)

        return conditions

    def _build_single_filter(self, filter_obj: MetadataFilter) -> Optional[FieldCondition]:
        """构建单个过滤器"""
        if filter_obj.operator == FilterOperator.EQ:
            # 处理单个值的等于比较
            if isinstance(filter_obj.value, list):
                # 如果值是列表，使用MatchAny
                return FieldCondition(
                    key=filter_obj.key,
                    match=MatchAny(any=filter_obj.value)
                )
            else:
                # 如果值是单个值，使用MatchValue
                return FieldCondition(
                    key=filter_obj.key,
                    match=MatchValue(value=str(filter_obj.value))
                )
        elif filter_obj.operator == FilterOperator.IN:
            # IN操作符应该使用MatchAny
            values = filter_obj.value if isinstance(filter_obj.value, list) else [filter_obj.value]
            return FieldCondition(
                key=filter_obj.key,
                match=MatchAny(any=[str(v) for v in values])
            )
        elif filter_obj.operator == FilterOperator.NE:
            # 处理不等于比较 - 使用MatchExcept来实现NOT操作
            user_logger.info(f"Processing NE operator for key: {filter_obj.key}, value: {filter_obj.value}")
            if isinstance(filter_obj.value, list):
                # 不等于任何一个值（即：不在列表中）
                return FieldCondition(
                    key=filter_obj.key,
                    match=MatchExcept(**{"except": [str(v) for v in filter_obj.value]})
                )
            else:
                # 不等于单个值
                return FieldCondition(
                    key=filter_obj.key,
                    match=MatchExcept(**{"except": [str(filter_obj.value)]})
                )
        else:
            user_logger.warning(f"Unsupported filter operator: {filter_obj.operator}")
            return None

    def _point_to_node(self, scored_point, index: Optional[VectorIndex] = None) -> BaseNode:
        """将Qdrant点转换为节点"""
        from init.settings import user_logger

        payload = scored_point.payload or {}
        user_logger.info(f"[QdrantVectorDB._point_to_node] 原始payload: {payload}")

        # 提取关系信息
        relationships_str = payload.get(FIELD_RELATIONSHIPS)
        relationships = {} if relationships_str is None else json.loads(relationships_str)

        # 直接使用payload作为metadata基础
        metadata = dict(payload)

        # 移除内部管理字段
        for field in [FIELD_RELATIONSHIPS, 'original_node_id']:
            metadata.pop(field, None)

        # 恢复关系信息到metadata中
        metadata[FIELD_RELATIONSHIPS] = relationships

        # 确定节点类型
        node_type = NodeTypeEnum.TEXT.node_type_code
        if index and index.doc_type:
            node_type = index.doc_type
        elif payload.get('node_type'):
            node_type = payload.get('node_type')

        # 创建相应的节点 - 使用保存在payload中的原始node_id
        node_id = payload.get('original_node_id', str(scored_point.id))

        if node_type == NodeTypeEnum.TEXT.node_type_code:
            if 'context_id' in metadata:
                # 上下文节点
                contextual_relationship = {DocumentNodeRelationship.CONTEXTUAL_GROUP: []}
                node = TextNode(
                    id_=node_id,
                    metadata=metadata,
                    context_id=metadata.get('context_id'),
                    doc_relationships=contextual_relationship,
                )
            else:
                node = TextNode(
                    id_=node_id,
                    metadata=metadata,
                    embedding=scored_point.vector if hasattr(scored_point, 'vector') else None,
                )
        elif node_type == NodeTypeEnum.QA.node_type_code:
            node = QaNode(
                id_=node_id,
                metadata=metadata,
            )
        elif node_type == NodeTypeEnum.IMAGE.node_type_code:
            node = ImageNode(
                id_=node_id,
                metadata=metadata,
            )
        else:
            node = TextNode(
                id_=node_id,
                metadata=metadata,
            )

        return node

    def query_by_filter(
            self,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            document_ids: Optional[List] = None,
            filter_condition: Optional[Any] = None,  # 支持 Filter 或 MetadataFilters
            index: Optional[VectorIndex] = None,
            index_extend: Optional[IndexExtendTransformComponent] = None,
            **kwargs: Any
    ) -> List[BaseNode]:
        """通过过滤器查询 - 支持 MetadataFilters 和原生 Filter"""
        
        # 智能转换过滤器类型
        query_filter = filter_condition
        if filter_condition and hasattr(filter_condition, 'filters'):
            # 如果是 MetadataFilters 类型，转换为 Qdrant Filter
            query_filter = self._metadata_filters_to_qdrant_filter(filter_condition)
        if document_ids:
            id_condition = FieldCondition(
                key="id",
                match=MatchValue(value=document_ids if len(document_ids) > 1 else document_ids[0])
            )
            if query_filter:
                query_filter = Filter(
                    must=[query_filter, id_condition]
                )
            else:
                query_filter = Filter(must=[id_condition])

        # 执行滚动查询
        scroll_result = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=query_filter,
            limit=limit or 100,
            offset=offset or 0,
            with_payload=True,
            with_vectors=kwargs.get("with_vectors", False)
        )

        nodes = []
        for point in scroll_result[0]:  # scroll返回(points, next_page_offset)
            node = self._point_to_node(point, index)
            nodes.append(node)

        # 使用索引扩展组件设置节点内容
        if index_extend is not None:
            nodes = index_extend.batch_set_node_contents(nodes=nodes)

        return nodes

    def query_by_ids(self, ids: List[str], **kwargs) -> List[dict]:
        """根据ID查询文档"""
        from init.settings import user_logger

        try:
            if not ids:
                return []

            # 使用scroll查询指定ID的点
            points, _ = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="original_node_id",
                            match=MatchAny(any=ids)
                        )
                    ]
                ),
                limit=len(ids),
                with_payload=True
            )

            docs = []
            for point in points:
                doc = {
                    'id': point.payload.get('original_node_id', str(point.id)),
                    'content': point.payload.get('content', ''),
                    'metadata': point.payload or {}
                }
                docs.append(doc)

            user_logger.info(f"QdrantVectorDB.query_by_ids: Found {len(docs)} documents for {len(ids)} ids")
            return docs

        except Exception as e:
            user_logger.error(f"QdrantVectorDB.query_by_ids failed: {e}")
            return []

    def doc2node(self, doc, index=None):
        """将文档转换为节点"""
        from init.settings import user_logger

        try:
            # 如果doc是字典格式（从query_by_ids返回）
            if isinstance(doc, dict):
                metadata = doc.get('metadata', {})
                node_id = doc.get('id', 'unknown')
                content = doc.get('content', '')

                from bella_rag.schema.nodes import TextNode
                node = TextNode(
                    id_=node_id,
                    text=content,
                    metadata=metadata
                )
                user_logger.info(f"QdrantVectorDB.doc2node: Converted doc {node_id} to node")
                return node
            else:
                # 如果是其他格式，返回默认节点
                from bella_rag.schema.nodes import TextNode
                return TextNode(
                    id_="converted_node",
                    text="Converted document",
                    metadata={}
                )

        except Exception as e:
            user_logger.error(f"QdrantVectorDB.doc2node failed: {e}")
            from bella_rag.schema.nodes import TextNode
            return TextNode(id_="error_node", text="Error", metadata={})
