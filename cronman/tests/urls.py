"""Test project URLs."""
from django.conf.urls import url
from django.contrib import admin
from django.urls import include, path

#
# from rest_framework.routers import SimpleRouter
#
#
# router = SimpleRouter()

urlpatterns = [
    url('admin/', admin.site.urls),
]

print(f"=====> {urlpatterns}")
