from django.shortcuts import render, HttpResponse
import time
from common.tool.orm import DORM
from init.settings import user_logger, error_logger
from common.helper.keones_exception import CodeError
from common.helper.api import ApiReturn


# Create your views here.
def index(request):
    user_logger.debug("demo test index")
    return render(request, "app_demo/index.html", context={})


def mysqltestdemo(request):
    sql = "select * from user_info limit 10"
    res = DORM.execute_select_sql(sql)
    return HttpResponse(ApiReturn(ApiReturn.CODE_OK, body=res).to_json())


def errordemo(request):
    raise CodeError("CodeError errordemo")



