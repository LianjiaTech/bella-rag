from pydantic import BaseModel

from app.common.contexts import TraceContext
from bella_rag.utils.trace_log_util import trace


@trace("runIn")
def aa_test(a=12,b=6):
    return a/b


class TestLog(BaseModel):

    param1: int = 12
    param2: int = 6

    @trace("runIn")
    def test_log(self, a=12, b=6):
        return a/b


def test_log():
    TraceContext.trace_id = "run_12345"
    aa = aa_test(12,3)
    print(aa)
    TraceContext.trace_id = "run_54321"
    test = TestLog()
    bb = test.test_log(12,2)
    print(bb)

