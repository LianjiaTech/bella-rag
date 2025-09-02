class BusinessError(Exception):
    def __init__(self, error_msg):
        super().__init__()
        self.error_msg = error_msg


class CheckError(BusinessError):
    def __init__(self, error_msg):
        super().__init__(error_msg)


class ChunkOperateError(BusinessError):

    def __init__(self, error_msg):
        super().__init__(error_msg)


class UnsupportedTypeError(CheckError):
    def __init__(self, error_msg):
        super().__init__(error_msg)


class EsDataException(BusinessError):
    """Exception raised for errors in the data request process."""
    def __init__(self, error_msg):
        super().__init__(error_msg)


class FileNotFoundException(BusinessError):
    """文件查不到异常"""
    def __init__(self, error_msg):
        super().__init__(error_msg)


class FileCheckException(BusinessError):
    """文件校验异常"""
    def __init__(self, error_msg):
        super().__init__(error_msg)


class CodeError(ValueError):
    def __init__(self, error_msg):
        super(CodeError, self).__init__()
        self.error_msg = error_msg


class CodeErrorForFe(ValueError):
    def __init__(self, error_msg):
        super(CodeErrorForFe, self).__init__()
        self.error_msg = error_msg


class CodeErrorNoData(ValueError):
    def __init__(self, error_msg):
        super(CodeErrorNoData, self).__init__()
        self.error_msg = error_msg