# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

"""Test project URLs."""
from django.conf.urls import url
from django.contrib import admin

urlpatterns = [
    url('admin/', admin.site.urls),
]
