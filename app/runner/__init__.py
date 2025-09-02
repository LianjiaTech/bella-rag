from app.runner.rag_runner import RagRunner, PlanAndSolveStreamRunner

# ---------------------- 初始化rag runner池 -----------------------------#
rag_runners = {
    RagRunner.mode(): RagRunner,
    PlanAndSolveStreamRunner.mode(): PlanAndSolveStreamRunner
}
