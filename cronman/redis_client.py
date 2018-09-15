# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

from django.utils.module_loading import import_string

from cronman.config import app_settings
from cronman.exceptions import MissingDependency


def get_strict_redis(host=None, port=None, db=None):
    """Retrieves Redis client object (StrictRedis) using constructor function
    defined in settings (`CRONMAN_REDIS_CONSTRUCTOR`).
    """
    _get_strict_redis = import_string(app_settings.CRONMAN_REDIS_CONSTRUCTOR)
    return _get_strict_redis(host=host, port=port, db=db)


def get_strict_redis_default(host=None, port=None, db=None):
    """Retrieve Redis client object (StrictRedis) - default implementation."""
    try:
        from redis import StrictRedis
    except ImportError:
        raise MissingDependency(
            "Unable to import redis. "
            "CronRemoteManager requires this dependency."
        )

    host = host or app_settings.CRONMAN_REDIS_HOST
    port = port or app_settings.CRONMAN_REDIS_PORT
    db = db if db is not None else app_settings.CRONMAN_REDIS_DB

    return StrictRedis(host=host, port=port, db=db)
