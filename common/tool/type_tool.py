import json
import re
import time

from django.db.models.query_utils import DeferredAttribute
from django.shortcuts import HttpResponse


class TypeTool(object):

    @staticmethod
    def is_dict_json_string(baseobj):
        try:
            return isinstance(json.loads(baseobj), dict)
        except:
            return False

    @staticmethod
    def is_list_json_string(baseobj):
        try:
            return isinstance(json.loads(baseobj), list)
        except:
            return False

    @staticmethod
    def is_int(baseobj):
        try:
            int(baseobj)
            return True
        except:
            return False

    @staticmethod
    def is_float(baseobj):
        try:
            float(baseobj)
            return True
        except:
            return False

    @staticmethod
    def is_valid_date(date):
        """
        验证是否为日期格式
        :param self:
        :param date:
        :return:
        """
        try:
            if ":" in date:
                time.strptime(date, "%Y-%m-%d %H:%M:%S")
            else:
                time.strptime(date, "%Y-%m-%d")
            return True
        except:
            return False

    @staticmethod
    def is_django_model_db_col(baseobj):
        if isinstance(baseobj, DeferredAttribute):
            return True
        else:
            return False

    @staticmethod
    def is_class_http_response(baseobj):
        if isinstance(baseobj, HttpResponse):
            return True
        else:
            return False

    @staticmethod
    def is_email(baseobj):
        rule = '.*@[\w-]+(\.[\w-]+)+$'
        match = re.match(rule, baseobj.replace("+", ""))
        if match:
            return True
        else:
            return False


if __name__ == "__main__":
    print(TypeTool.is_email("Plat-A_.A+PP@lianjia.com"))
    print(TypeTool.is_email("Plat-A_.APP@lianjia.com"))
    print(TypeTool.is_email("ladfsdf12341aa@lianjia.com"))
    print(TypeTool.is_email("Plat-A_1@APP@lianjia.com"))
    print(TypeTool.is_email("Plat-A_1&&&APPlian@jia.com"))
