"""
使用工厂类进行向量存储和索引初始化
"""
from common.tool.vector_db_tool import vector_store, questions_vector_store
from bella_rag.vector_stores.elasticsearch import EmptyElasticsearchStore
from bella_rag.retrievals.retriever import EmptyRetriever
from bella_rag.vector_stores.factory import (
    register_index,
    get_index, has_index, get_store
)


# 全局变量（延迟初始化）
_initialized = False
_index = None
_question_index = None
_es_store = None

def _lazy_initialize():
    """延迟初始化所有索引和存储"""
    global _initialized, _index, _question_index, _es_store
    
    if _initialized:
        return
        
    try:
        # 延迟导入以避免Django model问题
        from app.services import embed_model, chunk_vector_index_structure, question_vector_index_structure
        from app.services.index_extend.db_transformation import ChunkContentAttachedIndexExtend, \
            QuestionAnswerAttachedIndexExtend

        # 索引扩展组件
        chunk_index_extend = ChunkContentAttachedIndexExtend()
        question_answer_extend = QuestionAnswerAttachedIndexExtend()

        # 注册chunk索引
        register_index(
            name="chunk_index",
            vector_store=vector_store,
            embed_model=embed_model,
            index_structure=chunk_vector_index_structure,
            index_extend=chunk_index_extend,
            description="文档内容索引"
        )

        # 注册qa索引
        register_index(
            name="question_index",
            vector_store=questions_vector_store,
            embed_model=embed_model,
            index_structure=question_vector_index_structure,
            index_extend=question_answer_extend,
            description="问题答案索引"
        )

        # 设置索引实例
        _index = get_index("chunk_index")
        _question_index = get_index("question_index")
        
        # ES store延迟加载
        _es_store = get_store("es_index") if has_index("es_index") else EmptyElasticsearchStore()
        
        _initialized = True
        
    except Exception as e:
        # 如果初始化失败，使用空实现
        from init.settings import user_logger
        user_logger.warning(f"Failed to initialize indexes: {e}")
        _es_store = EmptyElasticsearchStore()
        _initialized = True

def get_chunk_index():
    """获取chunk索引"""
    _lazy_initialize()
    return _index

def get_question_index():
    """获取问答索引"""
    _lazy_initialize()
    return _question_index

def get_es_store():
    """获取ES存储（动态检查）"""
    # 每次都检查ES索引是否存在，以支持动态注册
    if has_index("es_index"):
        return get_store("es_index")
    else:
        return EmptyElasticsearchStore()

# 向后兼容的属性访问
class _LazyModuleAttr:
    """延迟模块属性"""
    def __init__(self, getter_func):
        self.getter_func = getter_func
    
    def __getattr__(self, name):
        instance = self.getter_func()
        if instance is None:
            raise AttributeError(f"'{name}' not available")
        return getattr(instance, name)

# 延迟加载的模块级别变量
index = _LazyModuleAttr(get_chunk_index)
question_index = _LazyModuleAttr(get_question_index)
es_store = _LazyModuleAttr(get_es_store)

# 空检索器（直接可用）
empty_retriever = EmptyRetriever()