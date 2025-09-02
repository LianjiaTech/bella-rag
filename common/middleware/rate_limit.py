import json
import re
import time

import redis
from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin

from app.config.apollo_configs import rate_limit_config
from common.tool.redis_tool import redis_pool


class RateLimitMiddleware(MiddlewareMixin):
    """
    基于Redis的限流中间件
    """

    def __init__(self, get_response=None):
        super().__init__(get_response)

        # 配置需要限流的URL模式和对应的限流规则
        # 默认的限流配置
        self.rate_limit_rules = [
            {
                'pattern': r'^/api/rag/',  # RAG相关接口
                'max_requests': 5,  # 每秒最多5次请求
                'window_seconds': 1,  # 1秒时间窗口
                'key_prefix': 'rag_rate_limit'
            }
        ]

    def process_request(self, request):
        """
        在视图处理之前进行限流检查
        """
        # 获取请求路径
        path = request.path_info

        custom_rate_limit = rate_limit_config.rate_limit_config()
        limit_rules = custom_rate_limit if custom_rate_limit else self.rate_limit_rules
        # 检查是否匹配需要限流的URL模式
        for rule in limit_rules:
            if re.match(rule['pattern'], path):
                # 执行限流检查
                rate_limit_response = self._check_rate_limit(request, rule)
                if rate_limit_response:
                    return rate_limit_response

        return None  # 继续处理请求

    def _check_rate_limit(self, request, rule):
        """
        执行限流检查
        """
        # 获取ak作为限流key
        ak = request.META.get('HTTP_AUTHORIZATION', '')
        if not ak:
            return None

        # 构建Redis key
        redis_key = f"{rule['key_prefix']}:{ak}"

        try:
            # 获取Redis连接
            r = redis.Redis(connection_pool=redis_pool)

            current_time = int(time.time())

            # 使用Redis管道提高性能
            pipe = r.pipeline()

            # 移除窗口外的请求记录
            pipe.zremrangebyscore(redis_key, 0, current_time - rule['window_seconds'])

            # 获取当前窗口内的请求数量
            pipe.zcard(redis_key)

            # 添加当前请求时间戳
            pipe.zadd(redis_key, {
                str(current_time * 1000000 + int(time.time() * 1000000) % 1000000): current_time
            })

            # 设置key过期时间
            pipe.expire(redis_key, rule['window_seconds'] + 1)

            results = pipe.execute()

            current_requests = results[1]  # 当前窗口内的请求数量

            # 检查是否超过限制
            if current_requests >= rule['max_requests']:
                error_response = {
                    "code": 429,
                    "message": f"请求过于频繁，每{rule['window_seconds']}秒最多允许{rule['max_requests']}次请求",
                    "type": "rate_limit_exceeded",
                    "path": request.path_info,
                }

                # 记录限流日志
                from init.settings import user_logger
                user_logger.warning(f"Rate limit exceeded: {ak} -> {request.path_info}")

                return HttpResponse(
                    json.dumps(error_response, ensure_ascii=False),
                    status=429,
                    content_type='application/json'
                )

            return None  # 没有超过限制，继续处理

        except Exception as e:
            # Redis连接失败时，记录错误但不阻塞请求
            from init.settings import error_logger
            error_logger.error(f"Rate limit Redis error: {str(e)}")
            return None  # 继续处理请求


    def add_rate_limit_rule(self, pattern, max_requests, window_seconds, key_prefix):
        """
        动态添加限流规则
        """
        rule = {
            'pattern': pattern,
            'max_requests': max_requests,
            'window_seconds': window_seconds,
            'key_prefix': key_prefix
        }
        self.rate_limit_rules.append(rule)

    def remove_rate_limit_rule(self, pattern):
        """
        移除限流规则
        """
        self.rate_limit_rules = [
            rule for rule in self.rate_limit_rules
            if rule['pattern'] != pattern
        ]