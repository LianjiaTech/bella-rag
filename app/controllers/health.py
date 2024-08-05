import json

from django.http import HttpResponse


def health_liveness(request):
    return HttpResponse(json.dumps({"status": "UP"}))


def health_readiness(request):
    return HttpResponse(json.dumps({"status": "UP"}))