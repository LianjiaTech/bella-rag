from typing import List, Type

from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import BaseComponent

from app.plugin.plugins import Plugin
from app.strategy.retrieval import RetrievalMode
from bella_rag.postprocessor.node import ScorePostprocessor


def get_components_from_plugins(plugins: List[Plugin], component_type: Type[BaseComponent]) -> List[BaseComponent]:
    """从插件中获取组件"""
    components = []
    for plugin in plugins:
        if plugin.components:
            for component in plugin.components:
                if isinstance(component, component_type):
                    components.append(component)
    return components


def build_postprocessor_from_retrieve_param(score: float, top_k: int,
                                            retrieve_mode: RetrievalMode, **kwargs) -> List[BaseNodePostprocessor]:
    """从请求参数中构建后置处理器"""
    return [ScorePostprocessor(top_k=top_k, rerank_score_cutoff=score)
            if retrieve_mode == RetrievalMode.FUSION else ScorePostprocessor(top_k=top_k)]
