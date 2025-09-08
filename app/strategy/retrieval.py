from enum import Enum
from typing import List, Tuple
from typing import Union

from llama_index.core import VectorStoreIndex
from llama_index.core.base.base_retriever import BaseRetriever
from llama_index.core.retrievers.fusion_retriever import FUSION_MODES
from typing_extensions import Optional

from app.plugin.plugins import Plugin, Completer, Reranker, PluginStatus, ImageRecognizer
from app.plugin.plugins import RetrievePlugin
from app.services import chunk_vector_index_structure, es_index_structure, question_vector_index_structure
from app.strategy import index, question_index, empty_retriever
from common.helper.exception import UnsupportedTypeError
# 直接导入IndexExtend（这些是数据库相关的，不属于向量存储）
from app.services.index_extend.db_transformation import ChunkContentAttachedIndexExtend, QuestionAnswerAttachedIndexExtend

# 创建索引扩展实例
chunk_index_extend = ChunkContentAttachedIndexExtend()
question_answer_extend = QuestionAnswerAttachedIndexExtend()
from init.settings import RETRIEVAL, RERANK
from bella_rag.meta.meta_data import NodeTypeEnum
from bella_rag.retrievals.fusion_retriever import MultiRecallFusionRetriever, SimilarQueryFusionRetriever
from bella_rag.retrievals.retriever import VectorIndexRetriever
from bella_rag.transformations.index_extend.index_extend_transform_component import IndexExtendTransformComponent
from bella_rag.vector_stores.factory import has_index, get_index
from bella_rag.vector_stores.filters import builtin_filter_hooks
from bella_rag.vector_stores.index import BaseIndex, EXTRA
from bella_rag.vector_stores.types import MetadataFilter, MetadataFilters, FilterOperator


class UserMode(Enum):
    """用户模式，直接映射到检索模式和插件组合"""
    FAST = "fast"  # 极速模式：纯语义检索
    NORMAL = "normal"  # 正常模式：语义检索 + 补全
    ULTRA = "ultra"  # 超强模式：混合检索 + 图片OCR + 上下文补全
    DEEP = "deep"  # 深度模式：混合检索 + 图片OCR + 上下文补全 + 计划执行


class RetrievalMode(str, Enum):
    """rag检索器"""

    SEMANTIC = "semantic"  # 语义检索，默认策略
    KEYWORD = "keyword"  # 关键词检索
    FUSION = "fusion"  # 混合检索

    @staticmethod
    def get_retrieve_by_value(value: str):
        try:
            return RetrievalMode(value)
        except Exception:
            raise UnsupportedTypeError('unsupported retrieve mode: ' + value)


def _get_filters_by_plugins(plugins: List[Plugin]) -> List[MetadataFilter]:
    """根据检索插件补充检索过滤条件"""
    metadata_filters = []
    for plugin in plugins:
        if isinstance(plugin, RetrievePlugin):
            metadata_filters.extend(plugin.get_metadata_filters())
    return metadata_filters


def _get_fusion_mode_by_retrieval_mode() -> FUSION_MODES:
    """当前默认只有一种混合检索策略"""
    return FUSION_MODES.RECIPROCAL_RANK


def create_retriever_by_mode(metadata_filters: MetadataFilters,
                             score: float,
                             file_ids: List[str],
                             retrieve_mode: RetrievalMode,
                             plugins: List[Plugin], ) -> BaseRetriever:
    """根据不同检索策略构建混合检索器"""
    if not file_ids:
        return empty_retriever

    fusion_mode = _get_fusion_mode_by_retrieval_mode()
    # 1.用户透传过滤规则
    filters = [metadata_filters] if metadata_filters else []
    # 2.元信息过滤规则
    combine_filters = []
    combine_filters.append(MetadataFilter(key="source_id", value=file_ids, operator=FilterOperator.IN))
    # 3.rag内置过滤逻辑
    combine_filters.extend(get_builtin_filters())
    # 4.插件过滤规则
    combine_filters.extend(_get_filters_by_plugins(plugins))

    # 去除重复过滤条件
    extras = []
    key_filters = {}
    for f in combine_filters:
        if f.key == EXTRA:
            extras.append(f)
        else:
            key_filters[f.key] = f
    filters.extend(list(key_filters.values()) + extras)

    # 初始化retrieve
    retrievers = [
        _create_base_vector_retriever(index, filters, index=chunk_vector_index_structure,
                                      retrieve_vector=False, index_extend=chunk_index_extend,
                                      similarity_cutoff=score),
        _create_base_vector_retriever(question_index, filters, index=question_vector_index_structure,
                                      retrieve_vector=False, index_extend=question_answer_extend,
                                      similarity_cutoff=score)]

    vector_retriever = SimilarQueryFusionRetriever(retrievers=retrievers,
                                                   similarity_top_k=int(RETRIEVAL['RETRIEVAL_NUM']))

    fusion_retrievers = [vector_retriever]
    if RetrievalMode.FUSION == retrieve_mode and has_index("es_index"):
        es_retriever = _create_base_vector_retriever(get_index("es_index"), filters, index=es_index_structure,
                                                     index_extends=[chunk_index_extend, question_answer_extend],
                                                     retrieve_vector=False)
        fusion_retrievers.append(es_retriever)

    # 构建多路检索器
    return MultiRecallFusionRetriever(retrievers=fusion_retrievers,
                                      similarity_top_k=int(RETRIEVAL['RETRIEVAL_NUM']),
                                      use_async=False,
                                      mode=fusion_mode)


def _create_base_vector_retriever(vector_store_index: VectorStoreIndex,
                                  metadata_filters: List[Union["MetadataFilters", MetadataFilter]],
                                  index: BaseIndex,
                                  index_extend: Optional[IndexExtendTransformComponent] = None,
                                  index_extends: Optional[List[IndexExtendTransformComponent]] = None,
                                  retrieve_vector: Optional[bool] = False,
                                  similarity_cutoff: Optional[float] = None) -> BaseRetriever:
    """构建基本向量检索器"""
    # filters校验
    filters = _check_filter_keys(metadata_filters, index.index_keys())

    vector_store_kwargs = {"index": index, "retrieve_vector": retrieve_vector,
                           "index_extends": index_extends, 'index_extend': index_extend}
    return VectorIndexRetriever(
        index=vector_store_index,
        similarity_top_k=int(RETRIEVAL['RETRIEVAL_NUM']),
        filters=MetadataFilters(filters=filters),
        vector_store_kwargs=vector_store_kwargs,
        similarity_cutoff=similarity_cutoff,
        rerank_threshold=float(RERANK['RERANK_THRESHOLD']),
    )


def _check_filter_keys(metadata_filters: List[Union["MetadataFilters", MetadataFilter]],
                       index_keys: List[str]) -> List[Union["MetadataFilters", MetadataFilter]]:
    """
    检查过滤条件的合法性
    （1）过滤的key必须是索引的key，不存在的key直接删除
    （2）只允许key为extra时有多个过滤条件
    """

    def clean_filters(filters):
        """递归清理过滤条件，删除无效的key"""
        cleaned_filters = []

        for filter_item in filters:
            if isinstance(filter_item, MetadataFilter):
                # 检查key是否在索引中，如果在则保留
                if filter_item.key in index_keys:
                    cleaned_filters.append(filter_item)
            elif isinstance(filter_item, MetadataFilters):
                # 递归处理嵌套的MetadataFilters
                cleaned_nested_filters = clean_filters(filter_item.filters)
                # 只有当清理后还有过滤条件时才保留这个MetadataFilters
                if cleaned_nested_filters:
                    new_metadata_filters = MetadataFilters(
                        filters=cleaned_nested_filters,
                        condition=filter_item.condition
                    )
                    cleaned_filters.append(new_metadata_filters)

        return cleaned_filters

    def extract_all_filters(filters):
        """递归提取所有的MetadataFilter用于检查重复key规则"""
        all_filters = []
        for filter_item in filters:
            if isinstance(filter_item, MetadataFilter):
                all_filters.append(filter_item)
            elif isinstance(filter_item, MetadataFilters):
                all_filters.extend(extract_all_filters(filter_item.filters))
        return all_filters

    # 第一步：清理无效的key
    cleaned_metadata_filters = clean_filters(metadata_filters)

    # 第二步：检查规则2 - 只允许key为extra时有多个过滤条件
    all_filters = extract_all_filters(cleaned_metadata_filters)
    key_counts = {}
    for filter_item in all_filters:
        key_counts[filter_item.key] = key_counts.get(filter_item.key, 0) + 1
        print(str(filter_item.key) + ": " + str(filter_item.operator) + ": " + str(filter_item.value))

    for key, count in key_counts.items():
        if count > 1 and key != "extra":
            raise ValueError(f"Multiple filters for key '{key}' are only allowed when key is 'extra'")

    return cleaned_metadata_filters


def get_builtin_filters() -> List[MetadataFilter]:
    """
    构建内置过滤器
    """
    # 默认不检索图片类型节点
    builtin_filters = [MetadataFilter(key='node_type', value=NodeTypeEnum.IMAGE.node_type_code,
                                      operator=FilterOperator.NE)]

    # 注入自定义的过滤逻辑
    if builtin_filter_hooks:
        for f in builtin_filter_hooks:
            builtin_filters.extend(f())
    return builtin_filters


def get_retrieval_config_from_user_mode(user_mode: str, **kwargs) -> Tuple[RetrievalMode, List[Plugin]]:
    """从用户模式直接获取检索配置"""
    if user_mode == UserMode.FAST.value:
        return RetrievalMode.SEMANTIC, [
            Reranker(status=PluginStatus.OFF, parameters={}),
            Completer(parameters={"complete_max_length": 1500, "complete_mode": "most_complete"}, **kwargs)
        ]
    elif user_mode in [UserMode.ULTRA.value, UserMode.DEEP.value]:
        return RetrievalMode.FUSION, [
            ImageRecognizer(parameters={"image_ocr_recognize": True}, **kwargs),
            Completer(parameters={"complete_max_length": 1500, "complete_mode": "context_complete"}, **kwargs),
            Reranker(parameters={}, **kwargs),
        ]
    else:
        # 默认使用normal模式
        return RetrievalMode.SEMANTIC, [
            Completer(parameters={"complete_max_length": 1500, "complete_mode": "most_complete"}, **kwargs),
            Reranker(parameters={}, **kwargs),
        ]


def get_retrieval_mode_from_user_mode(user_mode: str, **kwargs) -> RetrievalMode:
    """从用户模式获取检索模式"""
    retrieval_mode, _ = get_retrieval_config_from_user_mode(user_mode, **kwargs)
    return retrieval_mode


def build_plugins_from_user_mode(user_mode: str, **kwargs) -> List[Plugin]:
    """从用户模式构建插件"""
    _, plugins = get_retrieval_config_from_user_mode(user_mode, **kwargs)
    return plugins
