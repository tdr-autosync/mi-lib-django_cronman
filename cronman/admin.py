# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

from django.contrib import admin
from django.utils.module_loading import import_string

from cronman.config import app_settings
from cronman.forms import CronTaskAdminForm
from cronman.models import CronTask


admin_site_path = app_settings.CRONMAN_ADMIN_SITE

admin_site = import_string(admin_site_path) if admin_site_path else None


class CronTaskAdmin(admin.ModelAdmin):
    """Admin interface options for CronTask model"""

    form = CronTaskAdminForm
    list_display = (
        "job_spec",
        "start_at",
        "status",
        "user",
        "created_at",
        "started_at",
        "finished_at",
    )
    list_filter = ("status", "cron_job")
    max_num = 0

    def save_model(self, request, obj, form, change):
        """Assign current user to the task"""
        obj.user = request.user
        return super(CronTaskAdmin, self).save_model(
            request, obj, form, change
        )

    def get_fields(self, request, obj=None):
        """Fields: all fields on "edition", editable fields on addition"""
        if obj:
            fields = [
                "cron_job",
                "params",
                "start_at",
                "status",
                "user",
                "created_at",
                "started_at",
                "finished_at",
            ]
        else:
            fields = ["cron_job", "params", "start_at"]
        return fields

    def get_readonly_fields(self, request, obj=None):
        """Readonly Fields: all on "edition", none on addition"""
        if obj:
            readonly_fields = self.get_fields(request, obj)
        else:
            readonly_fields = []
        return readonly_fields


if admin_site:
    admin_site.register(CronTask, CronTaskAdmin)
