import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "init.settings")

django.setup()
import sys
from init.settings import OPENAPI
from app.response import default_event_handler
from app.services.file_service import file_indexing
from app.strategy.retrieval import get_retrieval_mode_from_user_mode, build_plugins_from_user_mode

sys.setrecursionlimit(10000)

# 环境变量添加open api信息
os.environ["OPENAI_API_KEY"] = OPENAPI["AK"]
os.environ["OPENAI_BASE_URL"] = OPENAPI["URL"]
from app.common.contexts import TraceContext
from app.services import ak
from app.services.rag_service import rag
from bella_rag.transformations.extractor.extract_context import context_summary
from bella_rag.utils.file_api_tool import file_api_client

'''
从文件上传到参与检索生成的demo示例
'''
# 1. 上传file
current_file_path = os.path.abspath(__file__)
current_directory = os.path.dirname(current_file_path)

file_path = current_directory.replace('/examples', '/tests/resources/测试.pdf')
with open(file_path, 'rb') as file:
    file_bytes = file.read()
    file_info = file_api_client.upload_file(file_bytes, '测试.pdf', 'assistants')
    file_id = file_info.get('id')

# 2. 文件解析
TraceContext.trace_id = file_id
file_indexing(file_id, "测试.pdf")

# 3. 背景信息总结
context_summary(file_id)

# 4. 构建rag参数
user_mode = 'normal'
# 检索插件
retrieve_mode = get_retrieval_mode_from_user_mode(user_mode)
plugins = build_plugins_from_user_mode(user_mode)

# 5. 调用rag方法
print(rag(query='应收账款的账龄分析',
          top_k=3, file_ids=[file_id], api_key=ak,
          model="gpt-5.4",
          retrieve_mode=retrieve_mode,
          plugins=plugins, event_handler=default_event_handler,
          ))
