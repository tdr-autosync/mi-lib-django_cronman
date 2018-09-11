# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

from django import forms
from django.utils.functional import cached_property
from django.utils.six import text_type

from cronman.job import cron_job_registry
from cronman.models import CronTask
from cronman.utils import cron_jobs_module_config, parse_params


class CronTaskAdminForm(forms.ModelForm):
    """Admin form for CronTask model"""

    class Meta:
        model = CronTask
        fields = ("cron_job", "params", "start_at")

    cron_job = forms.ChoiceField(choices=())

    def __init__(self, *args, **kwargs):
        super(CronTaskAdminForm, self).__init__(*args, **kwargs)
        if "cron_job" in self.fields:
            self.fields["cron_job"].choices = sorted(
                (name, name)
                for name, cron_job_class in cron_job_registry.items()
                if self.accept_cron_job_choice(name, cron_job_class)
            )

    @cached_property
    def allowed_tasks(self):
        """Allowed task (cron job) names"""
        return cron_jobs_module_config("ALLOWED_CRON_TASKS", default=())

    def clean_params(self):
        """Validate `params` field value"""
        params = self.cleaned_data.get("params") or ""
        try:
            parse_params(params)
        except ValueError as e:
            raise forms.ValidationError(text_type(e))
        return params

    def accept_cron_job_choice(self, name, cron_job_class):
        """Check if given cron job name and class can be accepted as 
        `cron_job` choice in this form.
        """
        return name in self.allowed_tasks
