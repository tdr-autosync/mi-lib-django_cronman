# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import os


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

_log_level = os.environ.get("TEST_CRONMAN_LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "django": {"handlers": ["console"], "level": _log_level},
        "cronman": {"handlers": ["console"], "level": _log_level},
    },
}
