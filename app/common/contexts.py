import contextvars

from bella_openapi.bella_trace._context import _TraceContext as OpenApiTraceContext

from common.helper.exception import CheckError

_user_context = contextvars.ContextVar("user_context", default=None)
query_embedding_context = contextvars.ContextVar("query_embedding", default=[])
_trace_progress_context = contextvars.ContextVar("trace_progress", default="")
_openapi_key_context = contextvars.ContextVar("ak", default="")


class _UserContext(object):
    @property
    def user_id(self) -> str:
        return _user_context.get()

    @user_id.setter
    def user_id(self, value):
        _user_context.set(value)


class TraceContext(OpenApiTraceContext):

    def __init__(self):
        super().__init__()

    @property
    def progress(self) -> str:
        return _trace_progress_context.get()

    @progress.setter
    def progress(self, value):
        _trace_progress_context.set(value)


class _OpenapiContext(object):
    @property
    def ak(self) -> str:
        ak = _openapi_key_context.get()
        if not ak:
            raise CheckError("open api key not set!")
        return ak

    @ak.setter
    def ak(self, value):
        _openapi_key_context.set(value)

UserContext = _UserContext()
TraceContext = TraceContext()
OpenapiContext = _OpenapiContext()