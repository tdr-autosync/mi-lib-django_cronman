# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import os
import platform
import tempfile


DEBUG = True

SECRET_KEY = "test-secret-key-n8gm2vaj43tqzh3yvbg9x1vj9f3m9mfcq7"

# SQLite:
DATABASES = {
    "default": {"NAME": ":memory:", "ENGINE": "django.db.backends.sqlite3"}
}

INSTALLED_APPS = (
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.admin",
    "cronman",
)

USE_I18N = True

LANGUAGE_CODE = "en"

# ROOT_URLCONF = "cronman.tests.urls"

_log_level = os.environ.get("TEST_CRON_LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "django": {"handlers": ["console"], "level": _log_level},
        "cronman": {"handlers": ["console"], "level": _log_level},
    },
}

# Settings for `cronman` app:

CRONMAN_DATA_DIR = os.path.join(tempfile.gettempdir(), "test.cronman")
CRON_DEBUG = True
# Module responsible for cron scheduler configuration,
# the list of tasks available to select (admin)
# and execute (cron machines):
CRON_JOBS_MODULE = None
CRON_NICE_CMD = "nice"
CRON_IONICE_CMD = "ionice" if platform.system() == "Linux" else None
CRON_REMOTE_MANAGER_ENABLED = True
# CRONMAN_ADMIN_SITE = "django.contrib.admin.site"
# Slack notifications settings:
SLACK_ENABLED = False
SLACK_URL = "https://fake-chat.slack.com/services/hooks/slackbot"
SLACK_TOKEN = "test-slack-token"
SLACK_DEFAULT_CHANNEL = "cron"
# Cronitor settings:
CRONITOR_ENABLED = False
CRONITOR_URL = "https://cronitor.link/{cronitor_id}/{end_point}"
# Absolute path to raven-cmd script
CRON_RAVEN_CMD = None
# Sentry configuration:
RAVEN_CONFIG = {"dsn": ""}
# Redis configuration:
# NOTE: Redis connections are mocked for tests.
# CRONMAN_REDIS_HOST = "127.0.0.1"
# CRONMAN_REDIS_PORT = 6379
# CRONMAN_REDIS_DB = 0
# CRONMAN_REDIS_CONSTRUCTOR = "cronman.redis_client.get_strict_redis_default"
