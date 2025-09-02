from typing import Callable, List, Optional

from bella_rag.vector_stores.types import MetadataFilter

FilterHook = Callable[[], List[MetadataFilter]]

builtin_filter_hooks: Optional[List[FilterHook]] = []   # 内置过滤器

def register_builtin_filter_hook(hook: FilterHook):
    global builtin_filter_hooks
    builtin_filter_hooks.append(hook)

