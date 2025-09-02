import json
from typing import List

from app.common.contexts import UserContext, OpenapiContext
from app.utils.llm_response_util import get_response_json_str
from deep_rag.common.contexts import DeepRagContext
from deep_rag.entity.exception import UnablePlanException
from deep_rag.entity.memory import MemoryItem, Memory
from deep_rag.entity.plan import Plan, Step, StepStatus, Action
from deep_rag.prompt.pipline import plan_prompt, multi_step_planning_prompt, re_planning_prompt, \
    conclusion_prompt, memory_evaluation_prompt, memory_combine_prompt
from deep_rag.tools.schemas import tool_list, search_tool, read_tool
from init.settings import OPENAPI, user_logger
from bella_rag.llm.openapi import OpenAPI

logger = user_logger


def get_llm(model: str):
    """
    llm初始化：不同场景可能使用不同模型
    """
    return OpenAPI(temperature=0.01, api_base=OPENAPI["URL"], api_key=OpenapiContext.ak,
                   timeout=300, model=model)


def plan(question: str) -> Plan:
    # 生成初始计划任务集
    prompt = plan_prompt.replace('$question', question).replace('$tool_list', str(tool_list))
    completion = get_llm('deepseek-chat').complete(prompt)
    res = completion.text
    logger.info(f"根据用户提问：{question} 生成计划任务列表：\n{res}")
    try:
        step_list = json.loads(get_response_json_str(res))
        p = Plan()
        for step in step_list:
            p.add_step(Step(description=step.get('description'),
                            dependencies=step.get('dependencies', []),
                            order=step.get('order')))
        return p
    except Exception:
        raise UnablePlanException(res)


def store_memory(question, task_order, step_result):
    summary_prompt = memory_evaluation_prompt.replace('$question', question).replace('$step_result', str(step_result))
    completion = get_llm('deepseek-reasoner').complete(summary_prompt)
    res = completion.text.strip()
    if "无相关内容" in res:
        # 无相关内容，信息无需添加至memory
        return

    memory = DeepRagContext.memory
    memory.conclusion_memory.append(
        MemoryItem(step_order=task_order, content=f'任务{task_order}执行参考信息：{res}', type='conclusion'))
    DeepRagContext.memory = memory


def execute_plan(p: Plan, question: str) -> (Plan, List[str]):
    # plan转成markdown任务清单（添加依赖执行的结果）
    plan_str = p.markdown_format_with_dependency_result()
    logger.info(f'开始执行计划：{p.markdown_format()}')

    # 从计划清单挑选任务执行
    execute_prompt = multi_step_planning_prompt.replace('$plan', plan_str).replace(
        '$tool_list', str(tool_list)).replace('$question', question)
    # 解析步骤执行
    task_result = get_llm('deepseek-chat').complete(execute_prompt).text
    logger.info(f'步骤解析：{task_result}')

    act_tool_mapping = {tool.metadata.name: tool for tool in [search_tool, read_tool]}

    # 提取任务标签和行动标签解析结构
    tasks = task_result.split("<任务>")
    parsed_data = []
    for task in tasks:
        if "</任务>" in task:
            # 提取任务序号
            task_number_part, rest = task.split("</任务>")
            task_number = task_number_part.replace("任务序号：", "").strip()

            # 提取行动部分
            if "<行动>" in rest and "</行动>" in rest:
                action_part = rest.split("<行动>")[1].split("</行动>")[0].strip()
                # 解析JSON
                action_json = json.loads(action_part)

                # 添加到结果列表
                parsed_data.append({"task_order": int(task_number), "tool_calls": action_json})

    task_steps = []
    step_orders = set()
    step_results = []
    # 执行任务
    for data in parsed_data:
        past_steps = []
        actions = []
        task_order = data["task_order"]
        tool_calls = data["tool_calls"]
        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "")
            input_params = tool_call.get("params", {})
            actions.append(Action(name=tool_name, params=input_params))
            if tool_name in act_tool_mapping:
                logger.info("工具执行开始：" + tool_name + str(input_params))
                tool_result = act_tool_mapping[tool_name].call(*input_params.values()).raw_output
                logger.info(f"工具执行结果：{tool_result}")

                # 更新计划
                past_steps.append(f"""当前步骤结果：\n- 工具：{tool_name}\n- 输入：{str(input_params)}\n- 输出：{tool_result}""")
            else:
                past_steps.append(f"工具不存在：{tool_name}")

        for step in p.get_all_steps():
            if step.order == task_order:
                # 记录任务执行结果到step里
                step.step_result = json.dumps(past_steps, ensure_ascii=False)
                # 更新step的状态
                step.status = StepStatus.COMPLETED
                step_orders.add(step.order)
                step.actions = actions
                # 添加依赖的序号
                for i in step._dependencies:
                    step_orders.add(i)
                step_results.append(f'任务{task_order}执行结果：{step.step_result}')
                # store_memory(question, task_order, step.step_result)

    # 每次execute执行的结果及其依赖的结果，添加到结果里
    for step in p.get_all_steps():
        if step.order in step_orders:
            logger.info(f'添加任务step结果，任务序号：{step.order}')
            task_steps.append(f'任务序号：{step.order}\n 任务执行情况：{step.step_result}\n')

    plan_sum_prompt = memory_combine_prompt.replace('$question', question).replace('$step_result',
                                                                                   str(step_results)).replace('$plan',
                                                                                                              p.markdown_format())
    completion = get_llm('deepseek-reasoner').complete(plan_sum_prompt)
    res = json.loads(get_response_json_str(completion.text.strip()))
    memory = DeepRagContext.memory
    memory.plan_memory.append(MemoryItem(step_order=-1, content=res.get('plan', ''), type='plan'))
    if "无相关内容" not in res.get('ref', ''):
        # 添加信息至memory
        memory.conclusion_memory.append(
            MemoryItem(step_order=-1, content=f"任务{str(step_orders)}执行参考信息：{res.get('ref', '')}",
                       type='conclusion'))
    DeepRagContext.memory = memory
    return p, task_steps


def replan(p: Plan, question: str, execute_steps: list) -> Plan:
    plan_str = p.markdown_format()
    origin_steps = p.get_all_steps()

    rp_prompt = (re_planning_prompt.replace('$origin_plan', plan_str)
                 .replace('$execute_steps', str(execute_steps))
                 .replace('$tool_list', str(tool_list)).replace('$question', question)
                 .replace('$memory', str([i.content for i in DeepRagContext.memory.plan_memory])))
    completion = get_llm('deepseek-reasoner').complete(rp_prompt)
    res = get_response_json_str(completion.text)
    logger.info(f"重新生成计划任务列表：\n{res}")
    step_list = json.loads(res)
    rp = Plan()
    for step in step_list:
        new_step = Step(description=step.get('description'),
                        dependencies=step.get('dependencies', []),
                        order=step.get('order'))
        if int(step.get('status')) == 1:
            new_step.status = StepStatus.COMPLETED
        if int(step.get('status')) == -1:
            new_step.status = StepStatus.ABORT
        rp.add_step(new_step)

    # 填充steps执行细节
    for i, step in enumerate(origin_steps):
        # 注：该情况下默认re-plan后只新增任务不变更原有任务
        rp.get_all_steps()[i].step_result = step.step_result
        rp.get_all_steps()[i].actions = step.actions

    return rp


def conclusion(question: str, p: Plan, memory: List[str], model: str) -> str:
    conclusion_prompt_detail = (conclusion_prompt.replace('$question', question)
                                .replace('$plan', p.markdown_format()).replace('$memory', str(memory)))
    return str(get_llm(model).complete(conclusion_prompt_detail))


def review_plan(p: Plan, rp: Plan) -> bool:
    """
    任务结束判断规则
    - 更新后的任务清单相比原始清单没有新增的任务
    - 更新后的任务清单所有任务均标记为已完成或已废弃
    """
    if len(p.get_all_steps()) != len(rp.get_all_steps()):
        return False

    for step in rp.get_all_steps():
        if step.status == StepStatus.NOT_STARTED:
            return False

    return True


def run_deep_rag(question: str,
                 file_ids: List[str],
                 user: str = None,
                 max_turns: int = 10,
                 model: str = "gpt-4o-mini") -> str:
    """
    执行planning and solve模式pipline
    1. plan(query) -> plan
    2. execute_plan(plan) -> plan
    3. replan(plan, query) -> (plan, steps)
    4. conclusion(plan, memory) -> Str
    """
    logger.info(f'deep rag start: {question}, file_ids: {file_ids}')
    # 初始化memory
    DeepRagContext.memory = Memory(conclusion_memory=[], plan_memory=[])
    # 初始化请求上下文
    DeepRagContext.query = question
    DeepRagContext.file_ids = file_ids
    UserContext.user_id = user

    # 任务开始执行
    execute_turns = 0
    try:
        # 1. 首次计划制定
        p = plan(question)
        while True:
            execute_turns += 1
            # 2. 执行计划
            p, steps = execute_plan(p, question)
            # 3. 重新制定计划
            rp = replan(p, question, execute_steps=steps)
            # 计划比对
            if review_plan(p, rp):
                logger.info("清单review完毕，任务结束")
                DeepRagContext.plan = rp
                return conclusion(question, rp, [i.content for i in DeepRagContext.memory.conclusion_memory], model)

            if execute_turns >= max_turns:
                return "执行次数超出最大限制"
            p = rp
    except UnablePlanException as e:
        return e.error_msg
