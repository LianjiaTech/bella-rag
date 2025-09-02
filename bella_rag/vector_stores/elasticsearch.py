import json
from typing import Optional, List, Any, Dict

from elasticsearch import Elasticsearch
from llama_index.core.vector_stores.types import VectorStoreQuery, VectorStoreQueryResult, BasePydanticVectorStore

from app.services import es_index_structure
from common.helper.exception import CheckError
from init.settings import user_logger
from bella_rag.schema.nodes import BaseNode, TextNode, QaNode, ImageNode, DocumentNodeRelationship
from bella_rag.transformations.index_extend.index_extend_transform_component import IndexExtendTransformComponent
from bella_rag.vector_stores.index import BaseIndex
from bella_rag.vector_stores.types import MetadataFilters


class ElasticsearchStore(BasePydanticVectorStore):
    """
    通用的Elasticsearch存储实现
    使用标准的elasticsearch-py客户端，不依赖特定业务逻辑
    """

    # Define Pydantic fields
    index_name: str = "es_store"
    es_client: Any = None
    batch_size: int = 200

    class Config:
        arbitrary_types_allowed = True

    def __init__(
            self,
            es_client: Optional[Any] = None,
            index_name: str = "es_store",
            batch_size: int = 200
    ) -> None:
        if es_client is None:
            raise ValueError("Elasticsearch client is required")

        super().__init__(stores_text=True)
        self.index_name = index_name
        self.es_client = es_client
        self.batch_size = batch_size

    def client(self):
        """获取Elasticsearch客户端"""
        return self.es_client

    def add(
            self,
            nodes: List[BaseNode],
            index: BaseIndex = es_index_structure,
            **add_kwargs: Any,
    ) -> List[str]:
        """
        Add nodes to Elasticsearch index.
        """
        ids = []
        for node in nodes:
            ids.append(node.node_id)
        storage_items = self._transform_nodes_to_storage_items(nodes, index)
        batch_items = [storage_items[i:i + self.batch_size] for i in range(0, len(storage_items), self.batch_size)]

        for batch in batch_items:
            self._store_batch(batch)
        return ids

    def _transform_nodes_to_storage_items(self, nodes: List[BaseNode], index: BaseIndex = es_index_structure) -> List[
        Any]:
        """将节点转换为存储项"""
        storage_items = []
        for node in nodes:
            doc_data = self.transform_node_to_doc(node, index)
            storage_item = self.create_storage_item(doc_data)
            storage_items.append(storage_item)
        return storage_items

    def transform_node_to_doc(self, node: BaseNode, index: BaseIndex = es_index_structure) -> Dict[str, Any]:
        """转换节点为通用文档格式"""
        metadata = node.metadata

        # 简单的extra处理
        extra = metadata.get('extra', [])
        if not isinstance(extra, list):
            extra = self._dict_to_extra_list(metadata)

        # 简单的关系处理
        relationships = {}
        if hasattr(node, 'doc_relationships') and node.doc_relationships:
            relationships = self._serialize_relationships(node.doc_relationships)

        res = {}
        if index.doc_type_key:
            res[index.doc_type_key] = node.get_node_type()
        if index.relationships_key:
            res[index.relationships_key] = json.dumps(relationships)
        if index.doc_id_key:
            res[index.doc_id_key] = metadata.get(index.doc_id_key, "")
        if index.text_key:
            res[index.text_key] = self._get_node_content(node)
        if index.doc_name_key:
            res[index.doc_name_key] = metadata.get(index.doc_name_key, "")
        res[index.extra_key] = extra
        res["_id"] = node.node_id
        return res

    def transform_doc_to_node(self, doc_id: str, doc: Dict[str, Any],
                              index: BaseIndex = es_index_structure) -> BaseNode:
        """转换文档为节点"""
        relationships_str = doc.get(index.relationships_key, '{}')
        relationships = json.loads(relationships_str) if relationships_str else {}

        metadata = doc.get('metadata', {})
        metadata.update({
            'relationships': relationships,
            'source_id': doc.get(index.doc_id_key),
            'source_name': doc.get(index.doc_name_key),
            'node_type': doc.get(index.doc_type),
        })

        node_type = doc.get(index.doc_type_key, 'text')
        node_id = doc_id

        # 根据节点类型创建对应的节点
        if node_type == 'text':
            if 'context_id' in metadata:
                # 上下文节点
                contextual_relationship = {DocumentNodeRelationship.CONTEXTUAL_GROUP: []}
                return TextNode(
                    id_=node_id,
                    metadata=metadata,
                    context_id=metadata.get('context_id'),
                    doc_relationships=contextual_relationship,
                )
            return TextNode(id_=node_id, metadata=metadata)
        elif node_type == 'qa':
            return QaNode(id_=node_id, metadata=metadata)
        elif node_type == 'image':
            return ImageNode(id_=node_id, metadata=metadata)
        else:
            return TextNode(id_=node_id, metadata=metadata)

    def _get_node_content(self, node: BaseNode) -> str:
        """获取节点内容"""
        if isinstance(node, QaNode):
            return node.get_content()
        else:
            return node.get_complete_content()

    def _dict_to_extra_list(self, data: dict) -> List[str]:
        """将字典转换为extra列表格式"""
        extra = []
        for k, v in data.items():
            if k in ['extra', 'relationships', 'document_id', 'document_name']:
                continue
            if isinstance(v, list):
                for item in v:
                    extra.append(f"{k}:{item}")
            else:
                extra.append(f"{k}:{v}")
        return extra

    def _serialize_relationships(self, relationships: dict) -> Dict[str, Any]:
        """序列化关系"""
        result = {}
        for key, value in relationships.items():
            key_str = key.value if hasattr(key, 'value') else str(key)

            if hasattr(value, 'node_id'):
                result[key_str] = value.node_id
            elif isinstance(value, list):
                result[key_str] = [item.node_id if hasattr(item, 'node_id') else str(item) for item in value]
            else:
                result[key_str] = str(value)
        return result

    def create_storage_item(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建存储项 - 返回标准的Elasticsearch文档"""
        return doc_data

    def _store_batch(self, batch: List[Dict[str, Any]], index: BaseIndex = es_index_structure) -> None:
        """存储批量数据到Elasticsearch"""
        actions = []
        for doc in batch:
            # 从doc中移除_id，因为它不应该在_source中
            doc_source = {k: v for k, v in doc.items() if k != "_id"}
            action = {
                "_index": self.index_name,
                "_id": doc["_id"],
                "_source": doc_source
            }
            actions.append(action)

        # 使用bulk API批量插入
        from elasticsearch.helpers import bulk, BulkIndexError
        try:
            bulk(self.es_client, actions)
        except BulkIndexError as e:
            user_logger.error(f"ES bulk index error: {e}")
            # 打印详细的错误信息
            for error in e.errors:
                user_logger.error(f"ES error detail: {error}")
            raise e

    def query(self, query: VectorStoreQuery, index: BaseIndex = es_index_structure,
              index_extends: List[IndexExtendTransformComponent] = None, **kwargs: Any) -> VectorStoreQueryResult:
        """查询向量存储"""
        query_str = query.query_str
        top_k = query.similarity_top_k

        # 构建Elasticsearch查询
        es_query = {
            "query": {
                "bool": {
                    "must": [{
                        "match": {
                            "content": {
                                "query": query_str
                            }
                        }
                    }]
                }
            },
            "size": top_k
        }

        # 添加过滤条件
        if query.filters:
            filter_conditions = self._build_es_filters(query.filters)
            es_query["query"]["bool"]["filter"] = filter_conditions

        # 执行查询
        response = self.es_client.search(index=self.index_name, body=es_query)

        # 处理结果
        ids = []
        nodes = []
        scores = []

        for hit in response['hits']['hits']:
            ids.append(hit['_id'])
            scores.append(hit['_score'])

            # 转换为节点
            doc_data = hit['_source']
            node = self.transform_doc_to_node(hit['_id'], doc_data, index)
            nodes.append(node)

        if index_extends:
            for index_extend in index_extends:
                deal_nodes = [node for node in nodes if isinstance(node, index_extend.support_node_type())]
                index_extend.batch_set_node_contents(deal_nodes)

        return VectorStoreQueryResult(nodes=nodes, ids=ids, similarities=scores)

    def delete(self, ref_doc_id: str, index: BaseIndex = es_index_structure, **delete_kwargs: Any) -> None:
        """删除文档"""
        # 构建删除查询
        delete_body = {
            "query": {
                "term": {es_index_structure.doc_id_key: ref_doc_id}
            }
        }

        # 物理删除：直接删除匹配的文档
        self.es_client.delete_by_query(index=self.index_name, body=delete_body)

    def delete_nodes(
            self,
            node_ids: Optional[List[str]] = None,
            filters: Optional[MetadataFilters] = None,
            **delete_kwargs: Any,
    ) -> None:
        """删除节点"""
        if not node_ids:
            return

        # 批量删除
        actions = []
        for node_id in node_ids:
            actions.append({
                "_op_type": "delete",
                "_index": self.index_name,
                "_id": node_id
            })

        from elasticsearch.helpers import bulk
        bulk(self.es_client, actions, ignore=[404])

    def _ensure_index_exists(self):
        """确保索引存在"""
        if not self.es_client.indices.exists(index=self.index_name):
            raise CheckError(f"Elasticsearch index does not exist. index_name: {self.index_name}")

    def _build_es_filters(self, filters: MetadataFilters) -> List[Dict[str, Any]]:
        """构建Elasticsearch过滤条件"""
        conditions = []

        for filter_item in filters.filters:
            if hasattr(filter_item, 'key') and hasattr(filter_item, 'value'):
                # 简单的term过滤
                if isinstance(filter_item.value, list):
                    operator = "terms"
                else:
                    operator = "term"
                conditions.append({
                    operator: {
                        f"{filter_item.key}": filter_item.value
                    }
                })

        return conditions


def create_elasticsearch_store(
        hosts: List[str] = None,
        index_name: str = "vector_store",
        **es_kwargs
) -> ElasticsearchStore:
    """
    创建通用的Elasticsearch存储实例

    Args:
        hosts: Elasticsearch主机列表，默认为['localhost:9200']
        index_name: 索引名称
        **es_kwargs: 传递给Elasticsearch客户端的其他参数

    Returns:
        GenericElasticsearchStore实例
    """
    if hosts is None:
        hosts = ['localhost:9200']

    default_kwargs = {
        'verify_certs': False,
        'ssl_show_warn': False,
        'request_timeout': 60
    }
    default_kwargs.update(es_kwargs)

    # 创建ES客户端
    es_client = Elasticsearch(hosts=hosts, **default_kwargs)

    try:
        if hasattr(es_client, '_client') and hasattr(es_client._client, '_headers'):
            es_client._client._headers = es_client._client._headers or {}
            es_client._client._headers.update({
                'Accept': 'application/vnd.elasticsearch+json; compatible-with=8'
            })
    except AttributeError:
        user_logger.warn('Elasticsearch client headers is not configured.')

    return ElasticsearchStore(
        es_client=es_client,
        index_name=index_name
    )


class EmptyElasticsearchStore(BasePydanticVectorStore):
    """
    es store空实现
    """

    # Define Pydantic fields
    index_name: str = "es_store"

    class Config:
        arbitrary_types_allowed = True

    def __init__(
            self,
            index_name: str = "es_store",
    ) -> None:
        super().__init__(stores_text=True)
        self.index_name = index_name

    def client(self):
        return None

    def add(
            self,
            nodes: List[BaseNode],
            index: BaseIndex = es_index_structure,
            **add_kwargs: Any,
    ) -> List[str]:
        return []

    def query(self, query: VectorStoreQuery, index: BaseIndex = es_index_structure,
              index_extends: List[IndexExtendTransformComponent] = None, **kwargs: Any) -> VectorStoreQueryResult:
        return VectorStoreQueryResult(nodes=[], ids=[], similarities=[])

    def delete(self, ref_doc_id: str, index: BaseIndex = es_index_structure, **delete_kwargs: Any) -> None:
        return

    def delete_nodes(
            self,
            node_ids: Optional[List[str]] = None,
            filters: Optional[MetadataFilters] = None,
            **delete_kwargs: Any,
    ) -> None:
        return
