import json

from django.utils.deprecation import MiddlewareMixin

from init.settings import user_logger

logger = user_logger


class LogRequestResponseMiddleware(MiddlewareMixin):

    def __call__(self, request):
        self.log_request_auto(request)
        response = self.get_response(request)
        self.log_response(response)
        return response

    @staticmethod
    def log_request_auto(request):
        """
        判断是否有文件上传：
        - 有文件：只记录表单参数和文件名
        - 无文件：记录完整 body
        """
        logger.info("Request Method: %s", request.method)
        logger.info("Request Path: %s", request.path)
        logger.info("GET Parameters: %s", request.GET.dict())
        logger.info("POST Parameters: %s", request.POST.dict())

        if getattr(request, "FILES", None) and request.FILES:
            # 文件上传请求
            logger.info("FILES: %s", list(request.FILES.keys()))
        else:
            # 普通请求，打印 body
            if request.body:
                try:
                    logger.info("Body: %s", json.loads(request.body))
                except json.JSONDecodeError:
                    logger.info("Body (raw): %s", request.body)

    @staticmethod
    def log_response(response):
        logger.info("Response Status Code: %s", response.status_code)
        if hasattr(response, 'content'):
            try:
                logger.info("Response Content: %s", json.loads(response.content))
            except json.JSONDecodeError:
                logger.info("Response Content: %s", response.content)