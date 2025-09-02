import copy
import json
from typing import List

from app.config.apollo_configs import file_access_config
from app.utils.convert import parse_relationships
from common.helper.exception import FileCheckException
from bella_rag.schema.nodes import BaseNode, StructureNode, TabelNode, QaNode, ImageNode
from bella_rag.utils.encoding_util import remove_non_utf8_chars
from bella_rag.utils.schema_util import get_table_previous_level
from bella_rag.vector_stores.index import FIELD_RELATIONSHIPS


def merge_values(existing_value, new_value):
    # 根据需要自定义合并逻辑
    if isinstance(existing_value, list) and isinstance(new_value, list):
        return existing_value + new_value
    elif isinstance(existing_value, dict) and isinstance(new_value, dict):
        return {**existing_value, **new_value}
    elif isinstance(new_value, list):
        new_value.append(existing_value)
        return new_value
    else:
        return new_value


def parser_decorator(parse_nodes_func):
    def wrapper(*args, **kwargs):
        nodes: List[BaseNode] = parse_nodes_func(*args, **kwargs)

        if nodes and len(nodes) > file_access_config.enable_max_node_size():
            raise FileCheckException(f"文件切片数超出限制：{len(nodes)}，最大切片数量：{file_access_config.enable_max_node_size()}")
        # 元数据传递
        if nodes and kwargs.get('metadata'):
            for i, node in enumerate(nodes):
                # 合并metadata
                merged_metadata = {**node.metadata}
                kwargs_metadata = copy.deepcopy(kwargs.get('metadata', {}))
                for key, value in kwargs_metadata.items():
                    if key in merged_metadata:
                        merged_metadata[key] = merge_values(merged_metadata[key], value)
                    else:
                        merged_metadata[key] = value
                node.metadata = merged_metadata

                # node_type处理，以后可能QA对在一个collection中，那么将不在需要这个node_type
                node.metadata.update({"node_type": node.get_node_type()})

                # 为了实现upsert, 对node id进行编码，file_id + index = node_id
                node.id_ = merged_metadata.get("source_id") + "-" + str(i)

        for node in nodes:
            if isinstance(node, StructureNode):
                if isinstance(node, ImageNode):
                    node.image_ocr_result = remove_non_utf8_chars(node.image_ocr_result)
                else:
                    node.set_content(remove_non_utf8_chars(node.get_complete_content()))
                relationships = node.doc_relationships
                if relationships != {}:
                    # 添加节点relation信息
                    node.metadata[FIELD_RELATIONSHIPS] = json.dumps(parse_relationships(relationships))
            elif isinstance(node, QaNode):
                node.question_str = remove_non_utf8_chars(node.question_str)
                node.answer_str = remove_non_utf8_chars(node.answer_str)
            # todo 在节点extra内添加表格信息，后续table节点需重新设计
            elif isinstance(node, TabelNode):
                extra = node.metadata.get("extra", [])
                extra.append("table_id:" + get_table_previous_level(node.order_num_str))
                node.metadata.update({"extra": extra})
        return nodes

    return wrapper



