# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

from django.utils.module_loading import autodiscover_modules

from cronman.job import cron_job_registry

default_app_config = "cronman.apps.CronConfig"


def autodiscover():
    """Discovers `cron_jobs` modules in other apps,
    fills out `cron_job_registry`
    """
    autodiscover_modules("cron_jobs", register_to=cron_job_registry)
