from pydantic import BaseModel

from app.services.rag_service import rag
from ke_rag.utils.trace_log_util import trace_log, trace_context


@trace_log("runIn")
def aa_test(a=12,b=6):
    return a/b


class TestLog(BaseModel):

    param1: int = 12
    param2: int = 6

    @trace_log("runIn")
    def test_log(self, a=12, b=6):
        return a/b


def test_log():
    token = trace_context.set("run_12345")
    aa = aa_test(12,3)
    print(aa)
    trace_context.reset(token)
    trace_context.set("run_54321")
    test = TestLog()
    bb = test.test_log(12,2)
    print(bb)

def test_rag_log():
    token = trace_context.set("run_12345")
    file_ids = ["F855058341502746624"]
    print(rag(query='windows', top_k=3, file_ids=file_ids, score=0.01, api_key='f7mgL1xpLfNFy1A430nxLLuvwO16came',
              model='gpt-4'))
    trace_context.reset(token)