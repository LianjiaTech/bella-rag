import json
from typing import List, Dict, Union, Any
from typing import cast

from llama_index.core.schema import BaseNode

from app.models.chunk_content_attached_model import ChunkContentAttached
from app.models.question_answer_attached_model import QuestionAnswerIndexAttached
from app.response.entity import RagSearchData, RagSearchAnnotation, RagSearchDoc
from app.services import chunk_vector_index_structure
from init.settings import user_logger
from bella_rag.schema.nodes import TextNode, QaNode, ImageNode, DocumentNodeRelationship, RelatedNode, NodeWithScore

logger = user_logger


def parse_path_from_order_num(order_num_str: str) -> List:
    """
    从order_num_str解析数字层级路径

    Args:
        order_num_str: 层级字符串

    Returns:
        数字层级路径数组
        支持格式: "1.2.3" -> [1, 2, 3]
                "1.6.1.1.4-4-2-2" -> [1,6,1,1,[4,4,2,2]]
    """
    if not order_num_str:
        return []

    # 如果没有横杠，直接按点号分割
    if '-' not in order_num_str:
        return [int(x) for x in order_num_str.split('.') if x.isdigit()]
    
    # 有横杠的情况：找到最后一个点号的位置
    last_dot_index = order_num_str.rfind('.')
    if last_dot_index == -1:
        # 没有点号，整个都是横杠格式
        dash_numbers = [int(x) for x in order_num_str.split('-') if x.isdigit()]
        return [dash_numbers] if dash_numbers else []
    
    # 分离点号部分和横杠部分
    dot_part = order_num_str[:last_dot_index]
    dash_part = order_num_str[last_dot_index + 1:]
    
    # 解析两部分
    dot_numbers = [int(x) for x in dot_part.split('.') if x.isdigit()]
    dash_numbers = [int(x) for x in dash_part.split('-') if x.isdigit()]
    
    # 组合结果
    result = dot_numbers
    if dash_numbers:
        result.append(dash_numbers)
    
    return result

def get_root_paths_from_paths(paths: List[List]) -> List[List]:
    """
    从路径列表中获取最短的路径，删除被更短路径包含的路径
    
    如果一个路径是另一个路径的前缀，则保留较短的路径，删除较长的路径
    
    Args:
        paths: 所有节点的路径列表
        
    Returns:
        去重后的最短路径列表
    """
    if not paths:
        return []
    
    # 按路径长度排序，短的在前
    sorted_paths = sorted(paths, key=len)
    result = []
    
    for path in sorted_paths:
        # 检查当前路径是否被结果中的任何路径包含
        is_contained = False
        for existing_path in result:
            # 如果existing_path是path的前缀，则path被包含
            if (len(existing_path) <= len(path) and 
                path[:len(existing_path)] == existing_path):
                is_contained = True
                break
        
        # 如果当前路径没有被包含，加入结果
        if not is_contained:
            result.append(path)
    
    return sorted(result)


def parse_paths_from_node(node: BaseNode) -> List[List]:
    """
    获取所有参与补全的节点的路径信息，并返回子树的根节点路径
    
    Args:
        node: 节点对象
        
    Returns:
        子树根节点的路径数组，如 [[1, 1], [1, 2]]
    """
    paths = []
    
    # 通过get_complete_group_nodes获取所有参与补全的节点
    if hasattr(node, 'get_complete_group_nodes'):
        complete_group_nodes = node.get_complete_group_nodes()
        
        # 如果有补全节点组，获取所有节点的路径
        if complete_group_nodes:
            for complete_node in complete_group_nodes:
                # 过滤掉mock节点
                if getattr(complete_node, 'is_mock', False):
                    continue
                    
                order_num_str = getattr(complete_node, 'order_num_str', '')
                if order_num_str:
                    path = parse_path_from_order_num(order_num_str)
                    if path and path not in paths:  # 去重
                        paths.append(path)
        else:
            # 如果没有补全节点组，返回主节点路径
            main_order_num_str = getattr(node, 'order_num_str', '')
            if main_order_num_str:
                main_path = parse_path_from_order_num(main_order_num_str)
                if main_path:
                    paths.append(main_path)
                else:
                    logger.warning(f"Failed to parse main node path from order_num_str: '{main_order_num_str}' for node: {node.node_id}")
            else:
                logger.warning(f"Main node has no order_num_str: {node.node_id}")
    else:
        # 如果节点没有get_complete_group_nodes方法，返回主节点路径
        main_order_num_str = getattr(node, 'order_num_str', '')
        if main_order_num_str:
            main_path = parse_path_from_order_num(main_order_num_str)
            if main_path:
                paths.append(main_path)

    # 获取子树的根节点路径
    root_paths = get_root_paths_from_paths(paths)
    return root_paths

def convert_chunk_content_attached_list(nodes: List[BaseNode]) -> List[ChunkContentAttached]:
    result: List[ChunkContentAttached] = []
    for index, node in enumerate(nodes):
        r = convert_chunk_content_attached(index, node)
        if r:
            result.append(r)
    return result


def convert_chunk_content_attached(index: int, node: BaseNode) -> Union[ChunkContentAttached, None]:
    if isinstance(node, TextNode):
        text_node: TextNode = node
        return ChunkContentAttached(
            chunk_id=text_node.node_id,
            content_title=text_node.text,
            content_data=text_node.text,
            source_id=text_node.metadata.get("source_id"),
            chunk_pos=index,
            token=text_node.token,
            order_num=node.order_num_str)
    elif isinstance(node, QaNode):
        qa_node: QaNode = node
        return ChunkContentAttached(
            chunk_id=qa_node.node_id,
            content_title=qa_node.question_str,
            content_data=qa_node.answer_str,
            source_id=qa_node.metadata.get("source_id"),
            chunk_pos=index)
    elif isinstance(node, ImageNode):
        image_node: ImageNode = node
        return ChunkContentAttached(
            chunk_id=image_node.node_id,
            content_title=image_node.image_ocr_result,
            content_data=image_node.image_url,
            source_id=image_node.metadata.get("source_id"),
            chunk_pos=index,
            token=image_node.token,
            order_num=node.order_num_str)
    else:
        logger.info("不关注的类型 %s", type(node))
        return None



def extract_metadata_from_extra(extra: List[str]) -> Dict:
    # 创建空字典
    result_dict = {}
    if not extra:
        return result_dict

    # 遍历字符串列表
    for item in extra:
        # 使用split方法将字符串分割成键和值
        key, value = item.split(":", 1)
        # 将键值对添加到字典中
        if key in result_dict:
            result_dict[key].append(value)
        else:
            result_dict[key] = [value]
    return result_dict


def _extra_data_from_dict_to_list(extra: dict):
    # value可能是list，可能是单值
    extra_list = []
    for key, value in extra.items():
        if isinstance(value, list):
            for v in value:
                extra_list.append(key + ":" + str(v))
        else:
            extra_list.append(key + ":" + str(value))
    return extra_list


def trans_metadata_to_extra(metadata: dict):
    extra = []
    if metadata:
        for k, v in metadata.items():
            if isinstance(v, List):
                for e in v:
                    extra.append(f"{k}:{e}")
            else:
                extra.append(f"{k}:{v}")

    return extra


def parse_relationships(relationships: Dict[DocumentNodeRelationship, RelatedNode]) -> Dict[str, Union[str, List[str]]]:
    node_id_relation = {}
    for key in relationships:
        related_node = relationships.get(key)
        if isinstance(related_node, BaseNode):
            # 单节点
            node_id_relation[key.value] = related_node.node_id
        elif key == DocumentNodeRelationship.CHILD:
            # child关系存在多个节点
            node_ids = []
            if related_node:
                # 仅需要添加子节点内第一个节点，通过链表还原全量子节点
                node_ids.append(related_node[0].node_id)
            node_id_relation[DocumentNodeRelationship.HEAD_CHILD.value] = node_ids

    return node_id_relation


def convert_question_answer_index_attached_list(nodes: List[BaseNode]) -> Union[
    List[QuestionAnswerIndexAttached], None]:
    qa_nodes: List[QaNode] = [cast(QaNode, node) for node in nodes if isinstance(node, QaNode)]
    if not qa_nodes:
        return None
    result = []
    for qa_node in qa_nodes:
        result.append(
            QuestionAnswerIndexAttached(source_id=qa_node.metadata.get("source_id"),
                                        group_id=qa_node.group_id,
                                        question=qa_node.question_str,
                                        answer=qa_node.answer_str,
                                        business_metadata=qa_node.business_metadata))
    return result


def convert_question_answer_attached(node: BaseNode) -> QuestionAnswerIndexAttached:
    return QuestionAnswerIndexAttached(source_id=node.metadata.get("source_id"),
                                       group_id=node.group_id,
                                       question=node.question_str,
                                       answer=node.answer_str)


def convert_score_nodes_to_search_res(score_nodes: List[NodeWithScore]) -> RagSearchData:
    docs = []
    for score_node in score_nodes:
        # 获取所有参与补全的节点路径
        paths = parse_paths_from_node(score_node.node)

        annotation = RagSearchAnnotation(
            file_id=score_node.metadata[chunk_vector_index_structure.doc_id_key],
            file_name=score_node.metadata[chunk_vector_index_structure.doc_name_key],
            paths=paths
        )
        docs.append(RagSearchDoc(
            type='text',
            annotation=annotation,
            score=score_node.score,
            text=score_node.get_content() if not isinstance(score_node.node,
                                                            BaseNode) else score_node.node.get_complete_content(),
        ))

    res = RagSearchData(docs=docs)
    logger.info(f"rag search result : {json.dumps(res.to_dict(), ensure_ascii=False)}")
    return res