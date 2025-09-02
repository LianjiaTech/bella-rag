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

    def init_stores(self):
        """初始化腾讯向量库存储实例"""
        user_logger.info("Initializing TencentVectorDB vector stores")

        # 公共配置
        common_config = {
            'stores_text': False,
            'url': TENCENT_VECTOR_DB["URL"],
            'key': TENCENT_VECTOR_DB["KEY"],
            'database_name': TENCENT_VECTOR_DB["DATABASE_NAME"],
        }

        # 初始化普通读实例
        self._stores['chunk'] = TencentVectorDB(
            collection_params=CollectionParams(
                dimension=int(TENCENT_VECTOR_DB["DIMENSION"]),
                collection_name=TENCENT_VECTOR_DB["COLLECTION_NAME"],
                drop_exists=False
            ),
            **common_config
        )

        self._stores['qa'] = TencentVectorDB(
            collection_params=CollectionParams(
                dimension=int(TENCENT_VECTOR_DB["DIMENSION"]),
                collection_name=TENCENT_VECTOR_DB["QUESTIONS_COLLECTION_NAME"],
                drop_exists=False
            ),
            **common_config
        )

        self._stores['summary'] = TencentVectorDB(
            collection_params=CollectionParams(
                dimension=int(TENCENT_VECTOR_DB["DIMENSION"]),
                collection_name=TENCENT_VECTOR_DB["SUMMARY_QUESTION_COLLECTION_NAME"],
                drop_exists=False
            ),
            **common_config
        )

        # 初始化强一致性读实例
        master_config = {**common_config, 'read_consistency': ReadConsistency.STRONG_CONSISTENCY}

        self._master_stores['chunk'] = TencentVectorDB(
            collection_params=CollectionParams(
                dimension=int(TENCENT_VECTOR_DB["DIMENSION"]),
                collection_name=TENCENT_VECTOR_DB["COLLECTION_NAME"],
                drop_exists=False
            ),
            **master_config
        )

        self._master_stores['qa'] = TencentVectorDB(
            collection_params=CollectionParams(
                dimension=int(TENCENT_VECTOR_DB["DIMENSION"]),
                collection_name=TENCENT_VECTOR_DB["QUESTIONS_COLLECTION_NAME"],
                drop_exists=False
            ),
            **master_config
        )

        self._master_stores['summary'] = TencentVectorDB(
            collection_params=CollectionParams(
                dimension=int(TENCENT_VECTOR_DB["DIMENSION"]),
                collection_name=TENCENT_VECTOR_DB["SUMMARY_QUESTION_COLLECTION_NAME"],
                drop_exists=False
            ),
            **master_config
        )

        # 设置过滤字段（所有实例使用默认的filter_fields配置）
        # 注意：filter_fields 在 TencentVectorDB 初始化时已经设置好了，这里不需要额外处理

        user_logger.info(f"TencentVectorDB stores initialized: {list(self._stores.keys())}")

    def get_chunk_store(self, master: bool = False) -> TencentVectorDB:
        """获取文档块存储"""
        return self._master_stores['chunk'] if master else self._stores['chunk']

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
