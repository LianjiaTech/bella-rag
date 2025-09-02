from app.services.question_answer_attached_service import QuestionAnswerIndexAttachedService
from init.settings import user_logger


def clear_deleted_qas_task():
    # 清理逻辑删掉的qa数据
    user_logger.info('start clear deleted qas')
    try:
        QuestionAnswerIndexAttachedService.delete_batches(500)
        user_logger.info('finish clear deleted qas')
    except Exception as e:
        user_logger.error(f'clear qas failed:{e}')
