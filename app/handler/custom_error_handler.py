from functools import wraps
from typing import Callable, List

from app.handler.exception_handler_funcs import report_callbacks
from init.settings import user_logger


ExceptionHandler = Callable[[str, Exception], None]
exception_handlers: List[ExceptionHandler] = [report_callbacks]


def custom_exception_handler():
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = repr(e)
                user_logger.error(
                    f'custom_exception_handler: {func_name} raised {error_msg}',
                    exc_info=True  # 记录堆栈跟踪
                )
                for handler in exception_handlers:
                    handler(func_name, e)
        return wrapper

    return decorator

