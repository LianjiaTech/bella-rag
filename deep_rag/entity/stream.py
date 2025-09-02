from dataclasses import dataclass, field
from enum import Enum
from typing import List, Any, Dict, Optional

from app.response.entity import Message, Content
from app.response.rag_response import OpenApiError
from deep_rag.entity.plan import Plan, Step


# 流式响应实体定义
class StreamEventType(Enum):
    PLAN_CREATE = "plan.create"
    PLAN_STEP_START = "plan.step.start"
    PLAN_STEP_COMPLETE = "plan.step.complete"
    PLAN_UPDATE = "plan.update"
    PLAN_COMPLETE = "plan.complete"
    MESSAGE_DELTA = "message.delta"
    ERROR = "error"
    HEARTBEAT = "healthy"


@dataclass
class MessageWithPlan(Message):
    """非流式响应"""
    plan: Optional[Plan] = None

    def __init__(self, content: List[Content], plan: Plan):
        super().__init__(content)
        self.plan = plan

    def to_dict(self) -> Dict[str, Any]:
        res = {
            'content': [c.to_dict() for c in self.content]
        }
        if self.plan:
            res["plan"] = self.plan.to_dict()
        return res


@dataclass
class StreamResponse:
    """流式响应基类"""
    event: StreamEventType
    id: str
    object: str
    reasoning_content: str = ""

    # plan相关
    plan: List[Step] = field(default_factory=list)
    step: Step = field(default_factory=dict)

    # message相关
    delta: Message = field(default_factory=dict)

    # error相关
    error: Optional[OpenApiError] = None

    def to_dict(self) -> Dict[str, Any]:
        res = {
            'id': self.id,
            'object': self.object,
        }
        if self.plan:
            res["plan"] = [s.to_dict() for s in self.plan]
        if self.step:
            res["step"] = self.step.to_dict()
        if self.reasoning_content:
            res["reasoning_content"] = self.reasoning_content
        if self.delta:
            res["delta"] = self.delta.to_dict()
        if self.error:
            res["error"] = self.error.json_response()
        return res
