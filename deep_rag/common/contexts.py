import contextvars

from common.helper.exception import CheckError
from deep_rag.entity.plan import Plan
from deep_rag.entity.memory import Memory

# 请求参数上下文
_query_context = contextvars.ContextVar("query", default="")
_file_ids_context = contextvars.ContextVar("file_ids", default=[])

## file_search参数
_file_search_params_context = contextvars.ContextVar("file_search_params", default={})

# 已搜索过的文件列表，用于search分页
_searched_files_context = contextvars.ContextVar("searched_files", default=[])

# memory信息
_memory_context = contextvars.ContextVar("memory", default=Memory(conclusion_memory=[], plan_memory=[]))

# plan信息
_plan_context = contextvars.ContextVar("plan", default=Plan())



class _DeepRagContext(object):
    @property
    def query(self) -> str:
        return _query_context.get()

    @query.setter
    def query(self, value):
        _query_context.set(value)

    @property
    def file_ids(self) -> list:
        return _file_ids_context.get()

    @file_ids.setter
    def file_ids(self, value):
        _file_ids_context.set(value)

    @property
    def file_search_params(self) -> dict:
        return _file_search_params_context.get()

    @file_search_params.setter
    def file_search_params(self, value):
        _file_search_params_context.set(value)

    @property
    def searched_files(self) -> list:
        return _searched_files_context.get()

    @searched_files.setter
    def searched_files(self, value):
        _searched_files_context.set(value)

    @property
    def memory(self) -> Memory:
        return _memory_context.get()

    @memory.setter
    def memory(self, value):
        _memory_context.set(value)

    @property
    def plan(self) -> Plan:
        return _plan_context.get()

    @plan.setter
    def plan(self, value):
        _plan_context.set(value)

    def clear_context(self):
        _query_context.set("")
        _file_ids_context.set([])
        _file_search_params_context.set({})
        _searched_files_context.set([])
        _memory_context.set(Memory(conclusion_memory=[], plan_memory=[]))
        _plan_context.set(Plan())


DeepRagContext = _DeepRagContext()
