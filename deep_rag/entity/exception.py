from common.helper.exception import BusinessError


class UnablePlanException(BusinessError):
    """计划无法制定异常"""

    def __init__(self, error_msg):
        super().__init__(error_msg)