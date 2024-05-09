import datetime
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse


class ApiReturn(object):
    # 1 开头的表示正常
    CODE_OK = 10000
    CODE_TIMEOUT = 10001
    CODE_NO_DATA = 10002

    # 2 开头的说明有问题，但是可接受
    CODE_WARNING = 20001

    # 3 开头的说明是出现了错误
    CODE_ERROR = 30001  # 出现错误，错误直接展示给用户
    CODE_SIGN_ERROR = 30011
    CODE_ERROR_FOR_FE = 31001  # 出现错误，错误展示给FE，由FE确定返回message

    # 4 开头的说明系统异常 或者 严重错误，需要赶紧解决的
    CODE_EXCEPTION = 41001
    CODE_FATAL_ERROR = 41002
    CODE_REQUEST_EXCEPTION = 41003
    CODE_URL_NOT_FOUND = 404
    CODE_USER_NOT_LOGIN = 44444  # 用户未登录
    CODE_USER_LOGIN_TIMEOUT = 44445  # 用户登录超时 2小时

    # 特殊状态码，表明服务已经停止
    CODE_STOP_SERVICE = 60001
    CODE_BLACK_LIST = 60002

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
