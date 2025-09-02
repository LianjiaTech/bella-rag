from enum import Enum
from typing import List, Dict, Any


class StepStatus(Enum):
    """步骤状态枚举"""
    NOT_STARTED = 0  # 未开始
    COMPLETED = 1  # 已完成
    ABORT = -1  # 步骤废弃


class Action:
    """行动项"""

    def __init__(self, name: str, params: Dict[str, Any]):
        self._name = name
        self._params = params

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self._name, "params": self._params}


class Step:
    """单个步骤的实体类"""

    def __init__(self, description: str, order: int, dependencies: List[int] = None, actions: List[Action] = None):
        self._description = description
        self._status = StepStatus.NOT_STARTED
        self._order = order
        self._step_result = ""
        self._dependencies = dependencies if dependencies is not None else []  # 依赖步骤
        self._actions = actions if actions is not None else []

    @property
    def description(self) -> str:
        return self._description

    @property
    def status(self) -> StepStatus:
        return self._status

    @status.setter
    def status(self, new_status: StepStatus):
        if not isinstance(new_status, StepStatus):
            raise ValueError("必须使用StepStatus枚举值")
        self._status = new_status

    @property
    def step_result(self) -> str:
        return self._step_result

    @step_result.setter
    def step_result(self, res: str):
        self._step_result = res

    @property
    def actions(self) -> List[Action]:
        return self._actions

    @actions.setter
    def actions(self, actions: List[Action]):
        self._actions = actions

    @property
    def order(self) -> int:
        return self._order

    def markdown_format(self) -> str:
        status_flag = ''
        if self._status == StepStatus.COMPLETED:
            status_flag = '✅'
        elif self._status == StepStatus.ABORT:
            status_flag = '❎'
        return f'{self._order}：[{status_flag}] {self._description}\n任务依赖：{str(self._dependencies)}\n'

    def __repr__(self):
        return f"Step {self.order}: {self.description} ({self.status.value})"

    def to_dict(self):
        res = {
            "description": self.description,
            "status": self.status.value,
            "order": self.order,
        }
        if self._step_result:
            res["result"] = self._step_result
        return res


class Plan:
    """计划清单管理类"""

    def __init__(self):
        self._steps: List[Step] = []

    def add_step(self, new_step: Step):
        """添加新步骤"""
        self._steps.append(new_step)

    def get_all_steps(self) -> List[Step]:
        """获取所有步骤"""
        return self._steps.copy()

    def get_step_by_order(self, order: int) -> Step:
        """按序号获取步骤"""
        if 1 <= order <= len(self._steps):
            return self._steps[order - 1]
        raise IndexError("无效的步骤序号")

    def get_steps_by_status(self, status: StepStatus) -> List[Step]:
        """按状态筛选步骤"""
        return [step for step in self._steps if step.status == status]

    def __len__(self):
        return len(self._steps)

    def markdown_format(self) -> str:
        plan_str = ""
        for step in self.get_all_steps():
            plan_str += step.markdown_format()
        return plan_str

    def markdown_format_with_dependency_result(self) -> str:
        plan_str = ""
        # 取剩余step中还依赖的结果
        dependency_orders = []
        for step in self.get_all_steps():
            # 遍历当前step，取出依赖步骤的结果
            if step.status == StepStatus.NOT_STARTED:
                dependency_orders.extend(step._dependencies)

        for step in self.get_all_steps():
            plan_str += step.markdown_format()
            if step.status == StepStatus.COMPLETED and step.order in dependency_orders:
                # 如果后续有步骤依赖于前面步骤的结果，添加执行明细
                plan_str += f'任务执行结果：{step.step_result}\n'
        return plan_str

    def to_dict(self):
        return {
            "steps": [s.to_dict() for s in self.get_all_steps()]
        }
