# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import os
import platform
import tempfile

from django.conf import settings

MYPY = False
if MYPY:
    from typing import Dict, Optional, Text


UNDEFINED = object()


class Setting(object):
    """AppSettings property."""

    def __init__(self, name, default):
        self.name = name
        self.default = default

    def __get__(self, instance, cls=None):
        if instance is None:
            return self
        return getattr(settings, self.name, self.default)


class AppSettings(object):
    """Class providing access to optional `cronman` app settings."""

    # General app settings:
    CRONMAN_DATA_DIR = Setting(
        "CRONMAN_DATA_DIR", os.path.join(tempfile.gettempdir(), "test.cronman")
    )  # type: Text
    CRONMAN_DEBUG = Setting("CRONMAN_DEBUG", False)  # type: bool
    # Module responsible for cron scheduler configuration,
    # the list of tasks available to select (admin)
    # and execute (cron machines):
    CRONMAN_JOBS_MODULE = Setting(
        "CRONMAN_JOBS_MODULE", None
    )  # type: Optional[Text]
    CRONMAN_NICE_CMD = Setting("CRONMAN_NICE_CMD", "nice")  # type: Text
    CRONMAN_IONICE_CMD = Setting(
        "CRONMAN_IONICE_CMD",
        "ionice" if platform.system() == "Linux" else None,
    )  # type: Optional[Text]
    CRONMAN_REMOTE_MANAGER_ENABLED = Setting(
        "CRONMAN_REMOTE_MANAGER_ENABLED", False
    )  # type: bool
    CRONMAN_ADMIN_SITE = Setting(
        "CRONMAN_ADMIN_SITE", "django.contrib.admin.site"
    )  # type: Optional[Text]

    # Slack notifications settings:
    CRONMAN_SLACK_ENABLED = Setting(
        "CRONMAN_SLACK_ENABLED", False
    )  # type: bool
    CRONMAN_SLACK_URL = Setting(
        "CRONMAN_SLACK_URL", None
    )  # type: Optional[Text]
    CRONMAN_SLACK_TOKEN = Setting(
        "CRONMAN_SLACK_TOKEN", None
    )  # type: Optional[Text]
    CRONMAN_SLACK_DEFAULT_CHANNEL = Setting(
        "CRONMAN_SLACK_DEFAULT_CHANNEL", None
    )  # type: Optional[Text]

    # Cronitor settings:
    CRONMAN_CRONITOR_ENABLED = Setting(
        "CRONMAN_CRONITOR_ENABLED", False
    )  # type: bool
    CRONMAN_CRONITOR_URL = Setting(
        "CRONMAN_CRONITOR_URL",
        "https://cronitor.link/{cronitor_id}/{end_point}",
    )  # type: Text

    # Sentry configuration:
    CRONMAN_SENTRY_ENABLED = Setting(
        "CRONMAN_SENTRY_ENABLED", False
    )  # type: bool
    CRONMAN_SENTRY_CONFIG = Setting(
        "CRONMAN_SENTRY_CONFIG", {"dsn": ""}
    )  # type: Dict
    # Absolute path to raven-cmd script (Sentry wrapper):
    CRONMAN_RAVEN_CMD = Setting(
        "CRONMAN_RAVEN_CMD", None
    )  # type: Optional[Text]

    # Redis configuration:
    CRONMAN_REDIS_HOST = Setting(
        "CRONMAN_REDIS_HOST", "127.0.0.1"
    )  # type: Text
    CRONMAN_REDIS_PORT = Setting("CRONMAN_REDIS_PORT", 6379)  # type: int
    CRONMAN_REDIS_DB = Setting("CRONMAN_REDIS_DB", 0)  # type: int
    CRONMAN_REDIS_CONSTRUCTOR = Setting(
        "CRONMAN_REDIS_CONSTRUCTOR",
        "cronman.redis_client.get_strict_redis_default",
    )  # type: Text


app_settings = AppSettings()
