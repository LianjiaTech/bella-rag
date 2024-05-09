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
