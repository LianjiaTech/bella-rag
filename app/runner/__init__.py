from app.runner.rag_runner import RagRunner, PlanAndSolveStreamRunner
from app.strategy.retrieval import UserMode

# ---------------------- 初始化rag runner池 -----------------------------#
rag_runners = {
    UserMode.FAST.value: RagRunner,
    UserMode.NORMAL.value: RagRunner,
    UserMode.ULTRA.value: RagRunner,
    UserMode.DEEP.value: PlanAndSolveStreamRunner
}
