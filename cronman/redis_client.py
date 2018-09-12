# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

from django.conf import settings
from django.utils.module_loading import import_string

from cronman.exceptions import MissingDependency


def get_strict_redis(host=None, port=None, db=None):
    """Retrieves Redis client object (StrictRedis) using constructor function
    defined in settings (`CRONMAN_REDIS_CONSTRUCTOR`).
    """
    _get_strict_redis = import_string(
        getattr(
            settings, "CRONMAN_REDIS_CONSTRUCTOR",
            "cronman.redis_client.get_strict_redis_default"
        )
    )
    return _get_strict_redis(host=host, port=port, db=db)


def get_strict_redis_default(host=None, port=None, db=None):
    """Retrieve Redis client object (StrictRedis) - default implementation."""
    try:
        from redis import StrictRedis
    except ImportError:
        raise MissingDependency(
            "Unable to import redis. "
            "CronRemoteManager requires redis < 2.11 to work."
        )

    host = host or settings.REDIS_HOSTNAME
    port = port or settings.REDIS_PORT
    db = db if db is not None else settings.REDIS_DB_ID
    client = StrictRedis(host=host, port=port, db=db)
    return client
