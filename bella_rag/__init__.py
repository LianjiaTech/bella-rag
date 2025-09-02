import os

from llama_index.core import Settings
from llama_index.core.callbacks.global_handlers import set_global_handler

# 获取当前文件的绝对路径
RAG_PATH = os.path.dirname(os.path.abspath(__file__))

set_global_handler("simple")

callback_manager = Settings.callback_manager