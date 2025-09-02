from deep_rag.tools.tools import FileSearchTool, ReadCheckTool

check_model = 'deepseek-reasoner'

# 初始化工具
file_search_tool = FileSearchTool()
read_check_tool = ReadCheckTool(check_model=check_model)
