from typing import Optional

from llama_index.vector_stores.tencentvectordb import CollectionParams
from tcvectordb.model.enum import ReadConsistency

from init.settings import QDRANT_VECTOR_DB
from init.settings import TENCENT_VECTOR_DB, user_logger
from bella_rag.vector_stores.qdrant import QdrantVectorDB
from bella_rag.vector_stores.tencentvectordb import TencentVectorDB, FilterField


class TencentStoreManager:
    """腾讯向量库存储管理器 - 统一管理所有TencentVectorDB实例"""

    def __init__(self):
        self._stores = {}
        self._master_stores = {}  # 强一致性读

    @staticmethod
    def _create_store(collection_name: str, master: bool = False) -> TencentVectorDB:
        """按统一配置创建客户端；并行任务可借此获得线程独占实例。"""
        config = {
            'stores_text': False,
            'url': TENCENT_VECTOR_DB["URL"],
            'key': TENCENT_VECTOR_DB["KEY"],
            'database_name': TENCENT_VECTOR_DB["DATABASE_NAME"],
        }
        if master:
            config['read_consistency'] = ReadConsistency.STRONG_CONSISTENCY
        return TencentVectorDB(
            collection_params=CollectionParams(
                dimension=int(TENCENT_VECTOR_DB["DIMENSION"]),
                collection_name=collection_name,
                drop_exists=False,
            ),
            **config,
        )

    def init_stores(self):
        """初始化腾讯向量库存储实例"""
        user_logger.info("Initializing TencentVectorDB vector stores")

        # 初始化普通读实例
        self._stores['chunk'] = self._create_store(
            TENCENT_VECTOR_DB["COLLECTION_NAME"],
        )
        self._stores['qa'] = self._create_store(
            TENCENT_VECTOR_DB["QUESTIONS_COLLECTION_NAME"],
        )
        self._stores['summary'] = self._create_store(
            TENCENT_VECTOR_DB["SUMMARY_QUESTION_COLLECTION_NAME"],
        )

        # 初始化强一致性读实例
        self._master_stores['chunk'] = self._create_store(
            TENCENT_VECTOR_DB["COLLECTION_NAME"],
            master=True,
        )
        self._master_stores['qa'] = self._create_store(
            TENCENT_VECTOR_DB["QUESTIONS_COLLECTION_NAME"],
            master=True,
        )
        self._master_stores['summary'] = self._create_store(
            TENCENT_VECTOR_DB["SUMMARY_QUESTION_COLLECTION_NAME"],
            master=True,
        )

        # 设置过滤字段（所有实例使用默认的filter_fields配置）
        # 注意：filter_fields 在 TencentVectorDB 初始化时已经设置好了，这里不需要额外处理

        user_logger.info(f"TencentVectorDB stores initialized: {list(self._stores.keys())}")

    def get_chunk_store(self, master: bool = False) -> TencentVectorDB:
        """获取文档块存储"""
        return self._master_stores['chunk'] if master else self._stores['chunk']

    def create_chunk_store(self, master: bool = False) -> TencentVectorDB:
        """创建独立的文档块存储客户端，供并行任务在线程内独占使用。"""
        return self._create_store(
            TENCENT_VECTOR_DB["COLLECTION_NAME"],
            master=master,
        )

    def rebuild_chunk_index(
            self,
            drop_before_rebuild: bool = False,
            throttle: Optional[int] = None,
    ) -> dict:
        """提交主 chunk 集合索引重建，并返回实际操作的集合标识。"""
        collection = self.get_chunk_store().collection
        user_logger.info(
            "提交主chunk集合索引重建: database=%s, collection=%s, "
            "dropBeforeRebuild=%s, throttle=%s",
            collection.database_name,
            collection.collection_name,
            drop_before_rebuild,
            throttle,
        )
        collection.rebuild_index(
            drop_before_rebuild=drop_before_rebuild,
            throttle=throttle,
        )
        return {
            'database': collection.database_name,
            'collection': collection.collection_name,
        }

    def get_chunk_index_status(self) -> dict:
        """通过 SDK 查询主 chunk 集合最新的索引任务状态。"""
        store = self.get_chunk_store()
        collection = store.collection
        latest_collection = store.describe_collection()
        return {
            'database': collection.database_name,
            'collection': collection.collection_name,
            'indexStatus': latest_collection.index_status,
        }

    def get_qa_store(self, master: bool = False) -> TencentVectorDB:
        """获取问答存储"""
        return self._master_stores['qa'] if master else self._stores['qa']

    def get_summary_store(self, master: bool = False) -> TencentVectorDB:
        """获取摘要存储"""
        return self._master_stores['summary'] if master else self._stores['summary']


class QdrantStoreManager:
    """Qdrant存储管理器 - 统一管理所有Qdrant实例"""

    def __init__(self):
        self._stores = {}

    def init_stores(self):
        """初始化Qdrant存储实例"""
        user_logger.info("Initializing Qdrant vector stores")

        # 公共配置
        common_config = {
            'stores_text': False,
            'url': QDRANT_VECTOR_DB["URL"] if QDRANT_VECTOR_DB["URL"] else None,
            'host': QDRANT_VECTOR_DB["HOST"] if not QDRANT_VECTOR_DB["URL"] else None,
            'port': QDRANT_VECTOR_DB["PORT"] if not QDRANT_VECTOR_DB["URL"] else None,
            'grpc_port': QDRANT_VECTOR_DB["GRPC_PORT"],
            'prefer_grpc': QDRANT_VECTOR_DB["PREFER_GRPC"],
            'api_key': QDRANT_VECTOR_DB["API_KEY"] if QDRANT_VECTOR_DB["API_KEY"] else None,
            'vector_size': QDRANT_VECTOR_DB["DIMENSION"],
            'batch_size': 100,
        }

        self._stores['chunk'] = QdrantVectorDB(
            collection_name=QDRANT_VECTOR_DB["COLLECTION_NAME"],
            **common_config
        )

        self._stores['qa'] = QdrantVectorDB(
            collection_name=QDRANT_VECTOR_DB["QUESTIONS_COLLECTION_NAME"],
            **common_config
        )

        self._stores['summary'] = QdrantVectorDB(
            collection_name=QDRANT_VECTOR_DB["SUMMARY_COLLECTION_NAME"],
            **common_config
        )

        user_logger.info(f"Qdrant stores initialized: {list(self._stores.keys())}")

    def get_chunk_store(self) -> QdrantVectorDB:
        """获取文档块存储"""
        return self._stores['chunk']

    def get_qa_store(self) -> QdrantVectorDB:
        """获取问答存储"""
        return self._stores['qa']

    def get_summary_store(self) -> QdrantVectorDB:
        """获取摘要存储"""
        return self._stores['summary']


qdrant_manager = QdrantStoreManager()
tencent_manager = TencentStoreManager()
