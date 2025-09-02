import datetime
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse


class ApiReturn(object):
    #  正常
    CODE_OK = 0

    # 通用http状态码异常，返回的状态码和HTTP的保持一直
    CODE_ERROR_FOR = 403
    CODE_URL_NOT_FOUND = 404
    CODE_METHOD_NOT_ALLOW = 405  # 请求方法不允许
    CODE_PARAM_NOT_ALLOW = 422  # 请求参数问题
    CODE_ERROR = 500  # 服务内部错误

    # 业务类异常
    CODE_BODY_INVALID_JSON_EXCEPTION = 10001  # Invalid JSON
    CODE_NO_DATA = 10002  # 没有数据
    CODE_BODY_PARAM_ERROR = 10003  # 请求体参数错误
    CODE_CREATE_FILE_INDEXING_ERROR = 10004  # 创建文件索引任务失败
    CODE_DELETE_FILE_INDEXING_ERROR = 10005  # 删除文件任务失败
    CODE_INNER_CODE = 10006  # 服务抛出异常,内部错误

    def __init__(self, code=CODE_OK, message="OK", body={}):
        self.__code = code
        self.__message = message
        self.__body = body

    @property
    def code(self):
        return self.__code

    @code.setter
    def code(self, code):
        self.__code = code

    @property
    def message(self):
        return self.__message

    @message.setter
    def message(self, message):
        self.__message = message

    @property
    def body(self):
        return self.__body

    @body.setter
    def body(self, body):
        if isinstance(body, bytes):
            body = str(body, encoding="utf-8")
        self.__body = body

    def to_json(self, is_unicode=False):
        ret_dict = {}
        ret_dict['code'] = self.code
        ret_dict['message'] = self.message
        if isinstance(self.body, bytes):
            self.body = str(self.body, encoding="utf-8")
        if not isinstance(self.body, dict) \
                and not isinstance(self.body, list) \
                and not isinstance(self.body, str) \
                and not isinstance(self.body, int) \
                and not isinstance(self.body, float) \
                and not isinstance(self.body, type(None)):
            ret_dict['body'] = "不识别的body类型！body必须是dict，list或者str/int/float。"
        else:
            if isinstance(self.body, dict):
                for k, v in self.body.items():
                    if isinstance(v, datetime.datetime):
                        # 如果是datetime类型的，无法转换为json，要先转换为字符串
                        self.body[k] = str(v)

            ret_dict['body'] = self.body

        return json.dumps(ret_dict, ensure_ascii=is_unicode, cls=DjangoJSONEncoder)


def json_response(code=ApiReturn.CODE_OK, message='OK', body={}):
    return HttpResponse(ApiReturn(code=code, message=message, body=body).to_json())


def format_chart_data(data):
    if not data.get('data'):
        return data
    data['data'] = [x for x in data['data'] if x["name"] not in ["待确认", "待商定"] or x["value"] != 0]
    if not data['data']:
        return {
            "data": [],
            "dimension": []
        }
    data['data'] = sorted(data['data'], key=lambda item: item['value'], reverse=True)
    total = 0
    for item in data['data']:
        total += item['value']
    for item in data['data']:
        item['rate'] = '%s%%' % round(item['value'] / total * 100, 2) if total > 0 else "0.0%"
    if len(data['data']) > 8:
        tmp_data = data['data']
        data['data'] = tmp_data[:8]
        other = tmp_data[8:]
        other_total = 0
        for item in other:
            other_total += item['value']
        data['data'].append({
            "name": "其他",
            "value": round(other_total, 2),
            "rate": '%s%%' % round(other_total / total * 100, 2) if total > 0 else "0.0%",
            "formatter": other})
    data['dimension'] = [item['name'] for item in data['data']]
    return data
