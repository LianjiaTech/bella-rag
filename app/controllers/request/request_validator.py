from common.helper.exception import CheckError

def validate_request_params(data):
    """
    校验请求参数是否有效
    """
    # 验证scope参数
    scope = data.get('scope', [])
    if not scope or len(scope) == 0:
        raise CheckError("请求中scope必传")
    
    for scope_item in scope:
        if not isinstance(scope_item, dict):
            raise CheckError("scope数组中的每个元素必须是对象")
        scope_type = scope_item.get('type')
        scope_ids = scope_item.get('ids', [])
        if not scope_type or not scope_ids:
            raise CheckError("scope中type和ids字段必传")
        if scope_type not in ['file', 'space']:
            raise CheckError("type只支持file和space类型")
        if not isinstance(scope_ids, list):
            raise CheckError("scope中ids必须是数组")

    # 验证response_type参数（如果存在）
    response_type = data.get('response_type', 'blocking')
    allowed_types = ['blocking', 'stream']
    if response_type not in allowed_types:
        raise CheckError(f"不支持的response_type: {response_type}")

    return True

