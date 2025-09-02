import os
from typing import Union

import chardet
from bella_openapi import StandardDomTree

from init.settings import user_logger


def get_file_type(file_path: str) -> str:
    """
    Get the file type from a file path.

    Args:
        file_path (str): The file path.

    Returns:
        str: The file type.
    """
    return file_path.split(".")[-1].lower()


def detect_encoding(byte_str: Union[bytes, bytearray]) -> str:
    """
    得到文件编码
    """
    result = chardet.detect(byte_str)
    encoding = result['encoding']
    user_logger.info("The encoding of the byte stream is %s", encoding)
    return encoding


def get_file_name(file_path: str) -> str:
    return os.path.basename(file_path)


def is_qa_knowledge(file_name: str) -> bool:
    """判断文件是否是qa知识"""
    return file_name is not None and file_name.lower().endswith('.csv')


def create_standard_dom_tree_from_json(json_data: dict) -> StandardDomTree:
    """
    从JSON数据创建StandardDomTree
    """
    from bella_openapi.entity.standard_domtree import StandardNode
    # 创建根节点
    root_node = StandardNode(**json_data)
    # 创建StandardDomTree
    return StandardDomTree(root=root_node)
