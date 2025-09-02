from enum import Enum
from typing import Optional, List

from pydantic import BaseModel


class NodeTypeEnum(Enum):
    TEXT = ("text", "文本")
    QA = ("qa", "QA")
    IMAGE = ("image", "图片")

    def __init__(self, node_type_code: str, node_type_name: str) -> None:
        self.node_type_code = node_type_code
        self.node_type_name = node_type_name


class NodeMetaData(BaseModel):
    # 文件FileId或者来源数据的唯一标识，使用@parser_decorator会自动注入，使用者不需要手动添加，会统一添加
    source_id: Optional[str] = None
    # 额外标量字段
    extra: Optional[List] = None
    # NodeTypeEnum
    node_type: Optional[str] = None
    # 存储的文本内容，可选择存索引里，也可以实现IndexExtendTransformComponent接口存放在别的存储介质中
    content_data: Optional[str] = None