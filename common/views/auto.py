from common.decorator.normal_decos import *
from init.settings import SERVER_START_TIME
from django.shortcuts import HttpResponse, redirect


def index(request):
    return HttpResponse("欢迎访问 My Django Project!")


def pub_check(request):
    return HttpResponse(json.dumps({"serverStartTime": SERVER_START_TIME}))
