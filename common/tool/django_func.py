import json
import urllib
import math
import re
import time

from django.shortcuts import HttpResponse
from django.db.models import *

from common.helper.api import ApiReturn
from common.tool.common_func import *
from common.tool.type_tool import TypeTool
from init.const import *
from init.settings import conf_dict


def get_request_ip(request):
    if 'HTTP_X_FORWARDED_FOR' in request.META:
        return request.META['HTTP_X_FORWARDED_FOR']
    if 'REMOTE_ADDR' in request.META:
        return request.META['REMOTE_ADDR']
    return "unknown"


def db_model_to_dict(db_model):
    res_dict = {}
    res_dict.update(db_model.__dict__)
    res_dict.pop("_state", None)  # 去除掉多余的字段
    for k, v in res_dict.items():
        if isinstance(v, datetime.datetime) or isinstance(v, datetime.date):
            # 如果是datetime类型的，无法转换为json，要先转换为字符串
            res_dict[k] = str(v).split(".")[0]
    return res_dict


def add_default_to_model(model_hand):
    for field in model_hand._meta.concrete_fields:
        # attr_list = str(field.get_cache_name).rstrip(">").split(":")
        attr_list = str(field.__repr__()).rstrip(">").split(":")
        field_name = attr_list[1].strip()
        field_type = attr_list[0].split(".")[-1].strip()
        if getattr(model_hand, field_name) is None:
            if field_name == "state":
                setattr(model_hand, field_name, 1)
            elif field_name in ["add_time", "mod_time"]:
                setattr(model_hand, field_name, get_current_time())
            elif field_type == "AutoField":
                pass
            elif field_type == "IntegerField":
                setattr(model_hand, field_name, 0)
            elif field_type == "FloatField":
                setattr(model_hand, field_name, 0.0)
            elif field_type == "CharField":
                setattr(model_hand, field_name, "")
            elif field_type == "TextField":
                setattr(model_hand, field_name, "")
            elif field_type == "DateField":
                setattr(model_hand, field_name, DEFAULT_DB_DATE)
            elif field_type == "DateTimeField":
                setattr(model_hand, field_name, DEFAULT_DB_TIME)
    return model_hand


def get_user_email_prefix(request):
    return request.META.get("HTTP_EMAIL_PREFIX", "")


def get_user_ucid(request):
    return request.META.get("HTTP_UCID", "")


def get_user_auth_id(request):
    exist = True
    auth_id = request.META.get("HTTP_AUTH_ID", None)
    if auth_id is None:
        auth_id = request.GET.get("auth_id")
        if auth_id is None:
            reqbody = request.body.decode("utf8")
            if TypeTool.is_dict_json_string(reqbody):
                body_dict = json.loads(reqbody)
                if "auth_id" in body_dict:
                    auth_id = body_dict["auth_id"]
                else:
                    exist = False
            else:
                exist = False
    if not exist:
        auth_id = 0
    return auth_id


def get_request_delete_id(request, name="id"):
    exist = True
    delete_id = request.GET.get(name)
    if delete_id is None:
        reqbody = request.body.decode("utf8")
        if TypeTool.is_dict_json_string(reqbody):
            body_dict = json.loads(reqbody)
            if name in body_dict:
                delete_id = body_dict[name]
            else:
                exist = False
        else:
            exist = False
    if not exist:
        delete_id = None
    return delete_id


def process_request_body_to_dict(request):
    reqbody = request.body.decode("utf8")
    if TypeTool.is_dict_json_string(reqbody):
        return json.loads(reqbody)
    else:
        return HttpResponse(ApiReturn(code=ApiReturn.CODE_ERROR, message="请求体必须是合法的json！", body={}).to_json())


def urlencode(basestr):
    return urllib.parse.quote(basestr)


def urldecode(basestr):
    return urllib.parse.unquote(basestr)


def transfer_percent_float(rate):
    return round(float(rate.replace('%', '')), 2)


def trans_django_dict_to_normal_dict(django_dict):
    retdict = {}
    for tmpkey, tmpvalue in django_dict.items():
        if isinstance(tmpvalue, str):
            retdict[tmpkey] = tmpvalue
        elif isinstance(tmpvalue, list):
            retdict[tmpkey] = tmpvalue[0]
        else:
            retdict[tmpkey] = str(tmpvalue)
    return retdict


if __name__ == "__main__":
    # sql = "SELECT * FROM pipeline_node_ext_attr GROUP by node_id"
    # print(json.dumps(res))
    get_file_content(download_url='http://api.ones.ke.com/attachment/keones/uploads/1573440700475247/变更SQL.txt')
