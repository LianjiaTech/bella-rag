import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "init.settings")  # 替换为你的 Django 项目的设置模块
django.setup()
print("@@@@@@@@@@@@@@@@@@@@@@@@@ ★★★INIT DJANGO SETTINGS★★★ @@@@@@@@@@@@@@@@@@@@@@@@@")
from ke_rag.utils.trace_log_util import trace_log, trace_context



@trace_log("runIn")
def aa_test(a=12,b=6):
    return a/b



def test_log():
    token = trace_context.set("run_12345")
    aa = aa_test(12,3)
    print(aa)
    trace_context.reset(token)
    trace_context.set("run_54321")
    aa = aa_test(12, 0)
    print(aa)