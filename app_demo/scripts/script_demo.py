"""
这是一个脚本示例，可以直接执行
"""
# 初始化系统环境变量配置
import os
import sys
current_path = os.path.dirname(os.path.abspath(__file__))
print(current_path)
rootpath = os.path.dirname(os.path.dirname(current_path)).replace("\\", "/")
print(rootpath)
syspath = sys.path
sys.path = []
sys.path.append(rootpath)  # 指定搜索路径绝对目录
sys.path.extend([rootpath + i for i in os.listdir(rootpath) if i[0] != "."])  # 将工程目录下的一级目录添加到python搜索路径中
sys.path.extend(syspath)

# setup django, 之后可以使用django的orm，框架中的service等
from init.init_django import *
from init.settings import conf_dict, redis_handle
from common.tool.orm import DORM
from common.tool.script_log import ScriptLog
script_logger = ScriptLog(level="DEBUG", max_log_count=20000)
script_logger.info(os.path.abspath(__file__))


def execute():
    # your script here
    pass


if __name__ == "__main__":
    execute()
