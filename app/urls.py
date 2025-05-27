from django.conf.urls import url

from app.controllers import rag, health, chunk, file, qa

urlpatterns = [

    url(r'^file/indexing$', rag.file_indexing, name="file_indexing"),
    url(r'^rag/rag_query$', rag.rag_query, name="rag_query"),

    url(r'^actuator/health/liveness$', health.health_liveness, name="health_liveness"),
    url(r'^actuator/health/readiness$', health.health_readiness, name="health_readiness")
]
