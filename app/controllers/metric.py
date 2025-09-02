from django.http import HttpResponse
from django.views.decorators.http import require_http_methods
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST


@require_http_methods(["GET"])
def metrics(request):
    metrics_page = generate_latest()
    return HttpResponse(metrics_page, content_type=CONTENT_TYPE_LATEST)
