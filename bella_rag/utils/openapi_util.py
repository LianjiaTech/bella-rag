import json
from functools import lru_cache

import requests
import tiktoken

from init.settings import OPENAPI, user_logger

DEFAULT_MODEL = 'gpt-4'

MOCK_MODEL = 'mock-model'


def fetch_model_data(model: str):
    headers = {
        "Authorization": OPENAPI["AK"]
    }
    response = requests.get(OPENAPI["URL"] + "/meta/model/info/" + model, headers=headers)
    return response.json()

@lru_cache(maxsize=128)
def openapi_model_info(model: str) -> dict:
    """一次性获取模型的所有信息"""
    if model == MOCK_MODEL:
        return {
            'context_window': 8192,
            'function_call': True,
            'support_temperature': True,
            'support_top_P': True,
            'support_max_tokens': True
        }

    data = fetch_model_data(model)
    properties = json.loads(data['data']['properties'])
    features = json.loads(data['data']['features'])

    return {
      'context_window': int(properties.get('max_input_context')),
      'function_call': bool(features.get('function_call')),
      'support_temperature': bool(features.get('support_temperature', True)),
      'support_top_P': bool(features.get('support_top_P', True)),
      'support_max_tokens': bool(features.get('support_max_tokens', True))
    }


def openapi_modelname_to_contextsize(model: str):
    return openapi_model_info(model)['context_window']

def openapi_is_function_calling_model(model: str):
    return openapi_model_info(model)['function_call']

def openapi_model_supported_params(model: str) -> dict:
    info = openapi_model_info(model)
    return {
        'temperature': info['support_temperature'],
        'top_p': info['support_top_P'],
        'max_tokens': info['support_max_tokens']
    }

def count_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    if not text:
        return 0
    # 用于计算token数的模型类型
    count_model = model
    # 自研模型均用gpt-4计算（可能有误差，可忽略）
    if not model.startswith("gpt-"):
        count_model = DEFAULT_MODEL
    encoding = tiktoken.encoding_for_model(count_model)
    tokens = encoding.encode(text)
    # 计算标记列表的长度，即标记的数量
    token_count = len(tokens)
    # 返回标记的数量
    return token_count


def str_token_limit(text: str, token_limit: int, model: str = DEFAULT_MODEL) -> str:
    if not token_limit:
        return text
    # 用于计算token数的模型类型
    count_model = model
    # 自研模型均用gpt-4计算（可能有误差，可忽略）
    if not model.startswith("gpt-"):
        count_model = DEFAULT_MODEL
    encoding = tiktoken.encoding_for_model(count_model)
    tokens = encoding.encode(text=text)
    truncated_tokens = tokens[:token_limit]
    return encoding.decode(tokens=truncated_tokens)


def valid_openapi_token(ak: str) -> bool:
    headers = {'Authorization': ak}
    response = requests.get(OPENAPI["URL"] + "/apikey/whoami", headers=headers)
    
    if int(response.status_code) != 200:
        return False
    
    try:
        data = response.json()
        return data.get("code") == 200
    except (ValueError, KeyError):
        return False


def fetch_ak_sha_by_code(ak_code: str) -> str:
    """
    根据 akcode 获取 akSha
    """
    headers = {
        "Authorization": OPENAPI["AK"]
    }
    
    url = f'{OPENAPI["URL"]}/console/apikey/fetchByCode'
    params = {'code': ak_code}

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    if data.get('code') == 200 and 'data' in data:
        return data['data'].get('akSha')
    else:
        user_logger.error("fetch ak sha failed : {}".format(ak_code))
        return None


def report_usage_log(
    user: str,
    model: str,
    usage: dict,
    ak_code: str = None,
    ak_sha: str = None,
    bella_trace_id: str = None,
    endpoint: str = "/v1/chat/completions"
) -> bool:
    """
    上报模型使用到 OpenAPI
    
    Args:
        user: 用户ID
        model: 模型名称
        usage: token 使用信息，包含 completion_tokens, prompt_tokens, total_tokens 等
        ak_code: API Key Code（如果未提供 ak_sha 则必须提供此参数）
        ak_sha: API Key SHA（可选，如果未提供则通过 ak_code 获取）
        bella_trace_id: Trace ID（可选）
        endpoint: API endpoint，默认为 /v1/chat/completions
    """
    try:
        # 构建请求数据
        log_data = {
            "user": user,
            "model": model,
            "endpoint": endpoint,
            "usage": usage
        }
        
        # 添加可选字段
        if ak_sha:
            log_data["akSha"] = ak_sha
        if ak_code:
            log_data["akCode"] = ak_code
        if bella_trace_id:
            log_data["bellaTraceId"] = bella_trace_id
        
        # 发送请求
        headers = {
            "Authorization": OPENAPI["AK"],
            "Content-Type": "application/json"
        }
        
        url = f'{OPENAPI["URL"]}/log'
        response = requests.post(url, headers=headers, json=log_data, timeout=5)
        response.raise_for_status()
        
        user_logger.info(f"Usage log reported successfully for user={user}, model={model}, total_tokens={usage.get('total_tokens', 0)}")
        return True
    except Exception as e:
        user_logger.error(f"Unexpected error when reporting usage log: {str(e)}")
        return False
