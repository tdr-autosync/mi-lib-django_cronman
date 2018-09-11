# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

from django.apps import AppConfig


class CronConfig(AppConfig):
    """Default AppConfig for cronman app."""

    name = "cronman"

    def ready(self):
        """Run app-specific code when Django starts"""
        from cronman import autodiscover

        autodiscover()
