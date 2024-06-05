from django.conf.urls import url

from app.views import main

urlpatterns = [
    url(r'^$', main.index, name="index"),
    url(r'^mysqltestdemo$', main.mysqltestdemo, name="mysqltestdemo"),
    url(r'^errordemo$', main.errordemo, name="errordemo"),
]
