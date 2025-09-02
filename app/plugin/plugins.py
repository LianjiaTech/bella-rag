from abc import abstractmethod
from enum import Enum
from typing import Dict, List, Optional

from llama_index.core.postprocessor.types import BaseNodePostprocessor
from llama_index.core.schema import BaseComponent

from app.services import chunk_vector_index_structure, EXTRA_DOC_TYPE_KEY
from common.helper.exception import UnsupportedTypeError
from init.settings import RETRIEVAL, RERANK
from bella_rag.meta.meta_data import NodeTypeEnum
from bella_rag.postprocessor.node import RebuildRelationPostprocessor, CompletePostprocessor, RerankPostprocessor, \
    ImageOcrPostprocessor
from bella_rag.providers import s3_storage
from bella_rag.utils.complete_util import Small2BigModes
from bella_rag.utils.rerank_tool import rerank
from bella_rag.vector_stores.types import MetadataFilter, FilterOperator


class PluginStatus(Enum):
    ON = "on"
    OFF = "off"

    @staticmethod
    def get_plugin_status_by_value(value: str):
        try:
            return PluginStatus(value)
        except Exception:
            raise UnsupportedTypeError('unsupported plugin status: ' + value)


class Plugin:
    """插件"""
    components: Optional[List[BaseComponent]] = None

    def __init__(self, name: str, parameters: Dict[str, any], status: PluginStatus = PluginStatus.ON, **kwargs):
        self.name = name
        self.status = status
        self.parameters = parameters
        self.init_components(**kwargs)

    def __repr__(self):
        return f"Plugin(name={self.name}, status={self.status}), parameters={self.parameters})"

    @abstractmethod
    def trans_to_components(self, **kwargs) -> List[BaseComponent]:
        """插件转llama index框架组件"""

    def init_components(self, **kwargs):
        """钩子方法，子类可以覆盖此方法以在初始化后执行额外的操作"""
        self.components = self.trans_to_components(**kwargs)


class RetrievePlugin(Plugin):
    """检索插件"""

    @abstractmethod
    def get_metadata_filters(self, **kwargs) -> List[MetadataFilter]:
        """根据检索插件的过滤条件"""


class Completer(RetrievePlugin):
    """补全器"""
    complete_max_length: int
    complete_mode: Small2BigModes

    def __init__(self, parameters: Dict[str, any], **kwargs):
        parameters = parameters or {}
        self.complete_max_length = parameters.get('complete_max_length', RETRIEVAL['COMPLETE_MAX_TOKEN'])
        self.complete_mode = Small2BigModes.get_small2big_mode_by_value(
            parameters.get('complete_mode', Small2BigModes.MOST_COMPLETE.value)
        )
        super().__init__(name="completer", parameters=parameters, **kwargs)

    def __repr__(self):
        return (f"CompleterPlugin(name={self.name}, complete_max_length={self.complete_max_length}, "
                f"complete_mode={self.complete_mode})")

    def get_metadata_filters(self, **kwargs) -> List[MetadataFilter]:
        """根据检索插件的过滤条件"""
        if self.complete_mode == Small2BigModes.CONTEXT_COMPLETE:
            # 需要补充上下文信息
            return []
        # 默认过滤上下文索引
        return [MetadataFilter(key=chunk_vector_index_structure.extra_key,
                               value=f'{EXTRA_DOC_TYPE_KEY}:contextual', operator=FilterOperator.EXClUDE)]

    def trans_to_components(self, **kwargs) -> List[BaseNodePostprocessor]:
        """根据检索后置处理器"""
        chunk_max_length = kwargs['max_tokens'] if 'max_tokens' in kwargs and kwargs['max_tokens'] is not None \
            else self.complete_max_length
        return [RebuildRelationPostprocessor(),
                CompletePostprocessor(chunk_max_length=chunk_max_length,
                                      small2big_strategy=self.complete_mode,
                                      **kwargs), ]


class Reranker(RetrievePlugin):
    """重排器"""
    rerank_num: int = 20

    def __init__(self, parameters: Dict[str, any], **kwargs):
        parameters = parameters or {}
        self.rerank_num = parameters.get('rerank_num', int(RERANK['RERANK_NUM']))
        super().__init__(name="reranker", parameters=parameters, **kwargs)

    def get_metadata_filters(self, **kwargs) -> List[MetadataFilter]:
        return []

    def trans_to_components(self, **kwargs) -> List[BaseNodePostprocessor]:
        """根据检索后置处理器"""
        return [RerankPostprocessor(rerank=rerank, rerank_num=self.rerank_num, top_k=kwargs.get('top_k', 3))]


class GeneratePlugin(Plugin):
    """生成插件"""

    @abstractmethod
    def get_prompt_constraint(self, **kwargs) -> str:
        """获取prompt约束"""


class ImageRecognizer(RetrievePlugin, GeneratePlugin):
    """图片识别器"""
    image_ocr_recognize: bool = False

    def __init__(self, parameters: Dict[str, any], **kwargs):
        parameters = parameters or {}
        self.image_ocr_recognize = parameters.get('image_ocr_recognize', False)
        super().__init__(name="image_recognizer", parameters=parameters, **kwargs)

    def get_metadata_filters(self, **kwargs) -> List[MetadataFilter]:
        return [MetadataFilter(key='node_type',
                               value=[member.node_type_code for member in NodeTypeEnum],
                               operator=FilterOperator.IN)] if self.image_ocr_recognize else []

    def trans_to_components(self, **kwargs) -> List[BaseNodePostprocessor]:
        # 如果没有S3存储，提供默认的URL签名函数
        if s3_storage and hasattr(s3_storage, 'sign_url'):
            image_url_signer = s3_storage.sign_url
        else:
            # 默认不加签，直接返回原URL
            def default_url_signer(url, *args, **kwargs):
                return url
            image_url_signer = default_url_signer
            
        return [ImageOcrPostprocessor(image_ocr_recognize=self.image_ocr_recognize, image_url_signer=image_url_signer)]

    def get_prompt_constraint(self, **kwargs) -> str:
        """获取prompt约束"""
        return """
            重点遵循以下要求：
            知识库可能包含两种信息类型：
            - 文本段落：直接用于回答问题
            - 图片元数据：包含URL和OCR解析的文字内容
            当参考信息包含与用户问题直接相关的图片信息时，必须在回答末尾用【参考图示】标注并完整呈现图片链接，若无图片链接则不需要标注【参考图示】
            链接插入需满足：
            图片内容与当前段落说明的流程/机制强相关
            保持自然衔接（例：具体流程可参考流程图【参考图示】）
            禁止修改或缩写原始链接
            禁止对无法解析OCR内容的图片做内容推测
            若检索结果包含多个相关链接，按出现顺序编号列出, 回答不添加任何总结性语句""" \
            if self.image_ocr_recognize else None


# 当前支持配置的插件池：插件类+是否默认开启的插件
plugin_pool = {
    'completer': Completer,
    'image_recognizer': ImageRecognizer,
    'reranker': Reranker,
}


def build_plugins(plugins: List[Plugin], **kwargs) -> List[Plugin]:
    """通过用户输入的plugin参数加工成实体"""
    process_plugins = []
    seen_plugins = {}  # 用于跟踪已经处理过的插件名称，同一插件不可重复传
    # 插件校验
    for plugin in plugins:
        if not plugin.name or plugin.name not in plugin_pool.keys():
            raise UnsupportedTypeError('unsupported plugin: ' + plugin.name)

        if plugin.name in seen_plugins.keys():
            raise ValueError(f'Duplicate plugin name detected: {plugin.name}')
        # 将插件名称添加到集合中
        seen_plugins[plugin.name] = plugin

    # 插件组装
    for plugin_name, plugin_class in plugin_pool.items():
        plugin = seen_plugins.get(plugin_name)
        # 插件关闭，则直接跳过
        if plugin and plugin.status == PluginStatus.OFF:
            continue

        # 从 plugin_pool 中获取对应的类并实例化
        initialized_plugin = plugin_class(parameters=plugin.parameters if plugin else {}, **kwargs)
        process_plugins.append(initialized_plugin)

    return process_plugins


def build_plugins_from_json(plugins_json, **kwargs) -> List[Plugin]:
    plugins = [Plugin(name=item['name'], parameters=item.get('parameters', {}),
                      # 插件默认状态为生效
                      status=PluginStatus.get_plugin_status_by_value(item.get('status', PluginStatus.ON.value)))
               for item in plugins_json]
    return build_plugins(plugins, **kwargs)
