import json
import traceback
import threading
import time
import queue
from typing import List, Dict, Any, Generator, Iterator

from app.common.contexts import UserContext, OpenapiContext
from app.plugin.plugins import Plugin
from app.response.entity import Message, Content, Text
from app.response.rag_response import OpenApiError
from app.services.rag_service import rag_streaming, rag
from app.strategy.retrieval import RetrievalMode
from app.utils.llm_response_util import get_response_json_str
from deep_rag.common.contexts import DeepRagContext
from deep_rag.entity.exception import UnablePlanException
from deep_rag.entity.memory import Memory, MemoryItem
from deep_rag.entity.plan import Plan, StepStatus, Step, Action
from deep_rag.entity.stream import StreamResponse, StreamEventType, MessageWithPlan
from deep_rag.pipline.plan_and_solve_runner import run_deep_rag, review_plan, replan, get_llm, plan
from deep_rag.prompt.pipline import multi_step_planning_prompt, memory_combine_prompt, conclusion_prompt
from deep_rag.tools.schemas import search_tool, read_tool, tool_list
from init.settings import user_logger
from bella_rag.handler.streaming_handler import BaseEventHandler
from bella_rag.vector_stores.types import MetadataFilters

logger = user_logger


class RagRunner:
    """支持流式和非流式输出的rag执行器"""

    def __init__(self, session_id: str, event_handler: BaseEventHandler):
        self.session_id = session_id
        self.event_handler = event_handler

    def rag_streaming(self, query: str,
                      top_k: int = 3,
                      file_ids: List[str] = None,
                      score: float = 0,
                      api_key: str = "",
                      model: str = "c4ai-command-r-plus",
                      instructions: str = "",
                      top_p: int = 1,
                      temperature: float = 0.01,
                      max_tokens: int = None,
                      metadata_filters: MetadataFilters = None,
                      retrieve_mode: RetrievalMode = RetrievalMode.SEMANTIC,
                      plugins: List[Plugin] = None,
                      show_quote: bool = False):
        return rag_streaming(query=query, top_k=top_k, file_ids=file_ids, api_key=api_key,
                             model=model, metadata_filters=metadata_filters, retrieve_mode=retrieve_mode,
                             plugins=plugins, show_quote=show_quote, event_handler=self.event_handler, )

    def rag(self, query: str,
            top_k: int = 3,
            file_ids: List[str] = None,
            score: float = 0,
            api_key: str = "",
            model: str = "c4ai-command-r-plus",
            instructions: str = "",
            top_p: int = 1,
            temperature: float = 0.01,
            max_tokens: int = None,
            metadata_filters: MetadataFilters = None,
            retrieve_mode: RetrievalMode = RetrievalMode.SEMANTIC,
            plugins: List[Plugin] = None,
            show_quote: bool = False):
        return rag(query=query, top_k=top_k, file_ids=file_ids, api_key=api_key,
                   model=model, metadata_filters=metadata_filters, retrieve_mode=retrieve_mode,
                   plugins=plugins, show_quote=show_quote, event_handler=self.event_handler, )

    @staticmethod
    def mode():
        return "normal"


class HeartbeatStreamWrapper:
    """心跳包流式包装器 - 真正的独立心跳发送"""
    
    def __init__(self, main_generator: Generator[str, None, None], session_id: str, heartbeat_interval: int = 10):
        self.main_generator = main_generator
        self.session_id = session_id
        self.heartbeat_interval = heartbeat_interval
        
    def __iter__(self):
        """使用超时机制来实现心跳包"""
        
        # 将主生成器转换为列表以便处理
        main_items = []
        main_thread = threading.Thread(target=self._collect_main_items, args=(main_items,))
        main_thread.daemon = True
        main_thread.start()
        
        last_heartbeat = time.time()
        main_index = 0
        
        while main_thread.is_alive() or main_index < len(main_items):
            current_time = time.time()
            
            # 检查是否有新的主流程项目
            if main_index < len(main_items):
                yield main_items[main_index]
                main_index += 1
                last_heartbeat = current_time
            else:
                # 检查是否需要发送心跳包
                if current_time - last_heartbeat >= self.heartbeat_interval:
                    heartbeat = StreamResponse(
                        event=StreamEventType.HEARTBEAT,
                        id=self.session_id,
                        object=StreamEventType.HEARTBEAT.value,
                    )
                    yield f"event: {heartbeat.event.value}\n"
                    yield f"data: {json.dumps(heartbeat.to_dict(), ensure_ascii=False)}\n\n"
                    last_heartbeat = current_time
                    logger.debug(f"Heartbeat sent for session {self.session_id}")
                
                # 短暂等待避免忙等待
                time.sleep(0.1)
    
    def _collect_main_items(self, items_list):
        """在独立线程中收集主生成器的项目"""
        try:
            for item in self.main_generator:
                items_list.append(item)
        except Exception as e:
            logger.error(f"Error in main generator: {e}")


class PlanAndSolveStreamRunner(RagRunner):
    """支持流式和非流式输出的 Plan and Solve Runner"""

    def __init__(self, session_id: str, event_handler: BaseEventHandler):
        super().__init__(session_id, event_handler)
        self.act_tool_mapping = {tool.metadata.name: tool for tool in [search_tool, read_tool]}

    def _convert_tool_calls_to_actions(self, tool_calls: List[Dict[str, Any]]) -> List[Action]:
        """将工具调用转换为ActionItem列表"""
        actions = []
        for tool_call in tool_calls:
            action = Action(
                name=tool_call.get("name", ""),
                params=tool_call.get("params", {})
            )
            actions.append(action)
        return actions

    def _create_stream_response(self, event_type: StreamEventType, object: str, **kwargs) -> StreamResponse:
        """创建流式响应"""
        response = StreamResponse(id=self.session_id, object=object, event=event_type, **kwargs)

        # 根据不同事件类型设置相应字段
        if 'plan' in kwargs:
            response.plan = kwargs['plan']
        if 'step' in kwargs:
            response.step = kwargs['step']
        if 'delta' in kwargs:
            response.delta = kwargs['delta']
        if 'content' in kwargs:
            response.content = kwargs['content']
        if 'reasoning_content' in kwargs:
            response.reasoning_content = kwargs['reasoning_content']
        if 'error' in kwargs:
            response.error = kwargs['error']

        return response

    def _emit_plan_event(self, plan: Plan, event_type: StreamEventType) -> StreamResponse:
        """发送计划创建事件"""
        return self._create_stream_response(
            event_type,
            event_type.value,
            plan=plan.get_all_steps(),
            reasoning_content=""
        )

    def _emit_plan_step_start(self, step_order: int, actions: List[Action]) -> StreamResponse:
        """发送步骤开始事件"""
        step_item = Step(
            description="",
            order=step_order,
            actions=actions
        )
        return self._create_stream_response(
            StreamEventType.PLAN_STEP_START,
            StreamEventType.PLAN_STEP_START.value,
            step=step_item,
            reasoning_content=""
        )

    def _emit_plan_step_complete(self, step_order: int, actions: List[Action],
                                 step_result: str) -> StreamResponse:
        """发送步骤完成事件"""
        step_item = Step(
            order=step_order,
            actions=actions,
            description="",
        )
        step_item.step_result = step_result
        step_item.step_status = StepStatus.COMPLETED
        return self._create_stream_response(
            StreamEventType.PLAN_STEP_COMPLETE,
            StreamEventType.PLAN_STEP_COMPLETE.value,
            step=step_item
        )

    def _emit_message_delta(self, delta_text: str) -> StreamResponse:
        """发送消息增量事件"""
        text = Text(value=delta_text, annotations=[])
        content = Content(type='text', text=[text])
        return self._create_stream_response(
            StreamEventType.MESSAGE_DELTA,
            StreamEventType.MESSAGE_DELTA.value,
            delta=Message(content=[content])
        )

    def _emit_error(self, error_code: str, error_type: str, error_message: str) -> StreamResponse:
        """发送错误事件"""
        error = OpenApiError(message=error_message,  body={"code": error_code, "type": error_type})
        return self._create_stream_response(
            StreamEventType.ERROR,
            StreamEventType.ERROR.value,
            error=error
        )

    def rag_streaming(self, query: str,
                      file_ids: List[str] = None,
                      model: str = "gpt-4o-mini",
                      metadata_filters: MetadataFilters = None,
                      retrieve_mode: RetrievalMode = RetrievalMode.SEMANTIC,
                      plugins: List[Plugin] = None,
                      **kwargs):
        """生成流式响应"""
        logger.info(f'deep rag start: {query}, file_ids: {file_ids}')
        ak = OpenapiContext.ak
        user = UserContext.user_id

        # 创建主流程生成器
        def main_stream():
            # 子线程上下文传递
            OpenapiContext.ak = ak
            UserContext.user_id = user
            DeepRagContext.clear_context()
            for stream_response in self.run_stream(query=query, file_ids=file_ids, model=model,
                                                   metadata_filters=metadata_filters,
                                                   retrieve_mode=retrieve_mode, plugins=plugins, **kwargs):
                # 将 StreamResponse 转换为event事件
                yield f"event: {stream_response.event.value}\n"
                yield f"data: {json.dumps(stream_response.to_dict(), ensure_ascii=False)}\n\n"
        
        # 使用心跳包装器
        heartbeat_wrapper = HeartbeatStreamWrapper(main_stream(), self.session_id)
        yield from heartbeat_wrapper

    def run_stream(self, query: str,
                   file_ids: List[str] = None,
                   model: str = "gpt-4o-mini",
                   metadata_filters: MetadataFilters = None,
                   retrieve_mode: RetrievalMode = RetrievalMode.SEMANTIC,
                   plugins: List[Plugin] = None,
                   max_turns: int = 10,
                   **kwargs) -> Generator[StreamResponse, None, None]:
        """流式执行 planning and solve 模式"""
        try:
            # 初始化
            DeepRagContext.memory = Memory(conclusion_memory=[], plan_memory=[])
            DeepRagContext.query = query
            DeepRagContext.file_ids = file_ids

            # 工具参数加载到上下文
            file_search_params = {
                "metadata_filters": metadata_filters,
                "retrieve_mode": retrieve_mode,
                "plugins": plugins,
            }
            DeepRagContext.file_search_params = file_search_params

            execute_turns = 0

            # 1. 首次计划制定
            p = plan(query)
            yield self._emit_plan_event(p, StreamEventType.PLAN_CREATE)

            while True:
                execute_turns += 1

                # 2. 执行计划 - 流式版本
                plan_stream = self._execute_plan_stream(p, query)
                steps = []
                for event in plan_stream:
                    if isinstance(event, tuple):  # 这是返回值 (p, steps)
                        p, steps = event
                        break
                    else:  # 这是 yield 的事件
                        yield event

                # 3. 重新制定计划
                rp = replan(p, query, execute_steps=steps)
                yield self._emit_plan_event(rp, StreamEventType.PLAN_UPDATE)

                # 计划比对
                if review_plan(p, rp):
                    logger.info("清单review完毕，任务结束")
                    yield self._emit_plan_event(rp, StreamEventType.PLAN_COMPLETE)

                    # 4. 流式输出结论
                    yield from self._conclusion_stream(query, rp,
                                                       [i.content for i in DeepRagContext.memory.conclusion_memory],
                                                       model)
                    break

                if execute_turns >= max_turns:
                    yield self._emit_error("max_turns_exceeded", "execution_limit", "执行次数超出最大限制")
                    break

                p = rp

        except UnablePlanException as e:
            yield self._emit_error("unable_plan", "planning_error", e.error_msg)
        except Exception as e:
            traceback.print_exc()
            yield self._emit_error("internal_error", "server_error", str(e))

    def _stream_step_execution(self, step_order: int, tool_calls: List[Dict[str, Any]]) -> Generator[
        StreamResponse, None, str]:
        """流式执行步骤"""
        actions = self._convert_tool_calls_to_actions(tool_calls)

        # 发送步骤开始事件
        yield self._emit_plan_step_start(step_order, actions)

        # 执行工具调用
        past_steps = []
        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "")
            input_params = tool_call.get("params", {})

            if tool_name in self.act_tool_mapping:
                logger.info("工具执行开始：" + tool_name + str(input_params))
                tool_result = self.act_tool_mapping[tool_name].call(*input_params.values()).raw_output
                logger.info(f"工具执行结果：{tool_result}")

                past_steps.append(
                    f"""当前步骤结果：\n- 工具：{tool_name}\n- 输入：{str(input_params)}\n- 输出：{tool_result}""")
            else:
                past_steps.append(f"工具不存在：{tool_name}")

        step_result = json.dumps(past_steps, ensure_ascii=False)

        # 发送步骤完成事件
        yield self._emit_plan_step_complete(step_order, actions, step_result)

        # 返回步骤执行结果
        return step_result

    def _execute_plan_stream(self, p: Plan, question: str):
        """流式执行计划"""
        # plan转成markdown任务清单（添加依赖执行的结果）
        plan_str = p.markdown_format_with_dependency_result()
        logger.info(f'开始执行计划：{p.markdown_format()}')

        # 从计划清单挑选任务执行
        execute_prompt = multi_step_planning_prompt.replace('$plan', plan_str).replace(
            '$tool_list', str(tool_list)).replace('$question', question)
        # 解析步骤执行
        task_result = get_llm('deepseek-chat').complete(execute_prompt).text
        logger.info(f'步骤解析：{task_result}')

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
            task_order = data["task_order"]
            tool_calls = data["tool_calls"]

            # 流式执行步骤 - 处理生成器的返回值
            step_generator = self._stream_step_execution(task_order, tool_calls)
            step_result = None
            try:
                while True:
                    event = next(step_generator)
                    yield event
            except StopIteration as e:
                # 获取生成器的返回值
                step_result = e.value

            # 更新计划
            for step in p.get_all_steps():
                if step.order == task_order:
                    step.step_result = step_result
                    step.status = StepStatus.COMPLETED
                    step_orders.add(step.order)
                    # 添加依赖的序号
                    for i in step._dependencies:
                        step_orders.add(i)
                    step_results.append(f'任务{task_order}执行结果：{step.step_result}')

        # 每次execute执行的结果及其依赖的结果，添加到结果里
        for step in p.get_all_steps():
            if step.order in step_orders:
                logger.info(f'添加任务step结果，任务序号：{step.order}')
                task_steps.append(f'任务序号：{step.order}\n 任务执行情况：{step.step_result}\n')

        plan_sum_prompt = memory_combine_prompt.replace('$question', question).replace('$step_result',
                                                                                       str(step_results)).replace(
            '$plan',
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

    def _conclusion_stream(self, question: str, p: Plan, memory: List[str], model: str) -> Generator[
        StreamResponse, None, None]:
        """流式输出结论"""
        conclusion_prompt_detail = (conclusion_prompt.replace('$question', question)
                                    .replace('$plan', p.markdown_format()).replace('$memory', str(memory)))

        completion_stream = get_llm(model).stream_complete(conclusion_prompt_detail)

        for chunk in completion_stream:
            if hasattr(chunk, 'delta') and chunk.delta:
                delta_text = chunk.delta
                yield self._emit_message_delta(delta_text)

    def rag(self, query: str,
            file_ids: List[str] = None,
            model: str = "gpt-4o-mini",
            metadata_filters: MetadataFilters = None,
            retrieve_mode: RetrievalMode = RetrievalMode.SEMANTIC,
            plugins: List[Plugin] = None,
            **kwargs):
        """非流式执行 planning and solve 模式"""
        DeepRagContext.clear_context()
        file_search_params = {
            "metadata_filters": metadata_filters,
            "retrieve_mode": retrieve_mode,
            "plugins": plugins,
        }
        DeepRagContext.file_search_params = file_search_params

        # 执行pipline
        answer = run_deep_rag(query, file_ids=file_ids, user=UserContext.user_id, model=model)
        message = self.event_handler.convert_query_res_to_rag_response(answer, [], [])
        return MessageWithPlan(content=message.content, plan=DeepRagContext.plan).to_dict()

    @staticmethod
    def mode():
        return "deep"
