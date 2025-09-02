from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class MemoryItem:
    step_order: int
    type: str
    content: Any  # 具体内容，可以是文本、结构化数据等
    metadata: Dict[str, Any] = field(default_factory=dict)  # 可选，附加信息


@dataclass
class Memory:
    conclusion_memory: List[MemoryItem] = field(default_factory=list)  # 可直接用于回答用户
    plan_memory: List[MemoryItem] = field(default_factory=list)  # 用于 agent 决策
