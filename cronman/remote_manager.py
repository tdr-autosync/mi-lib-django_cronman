# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import logging
import socket

from django.utils.functional import cached_property

# pylint: disable=E0401, E0611
from django.utils.six.moves import range

from cronman.base import BaseCronObject
from cronman.exceptions import MissingDependency
from cronman.redis_client import get_strict_redis
from cronman.taxonomies import CronSchedulerStatus
from cronman.utils import bool_param, config

logger = logging.getLogger("cronman.command.cron_remote_manager")


class CronRemoteManager(BaseCronObject):
    """Cron Manager: controls remote Cron Schedulers via Redis."""

    STATUS_KEY = "cron_scheduler:status:{host_name}"
    KILL_KEY = "cron_scheduler:kill:{host_name}"

    MAX_KILLS = 5

    def __init__(self, host_name=None, **kwargs):
        kwargs["logger"] = kwargs.get("logger", logger)
        super(CronRemoteManager, self).__init__(**kwargs)
        self.host_name = host_name or socket.gethostname()
        self.enabled = bool_param(config("CRONMAN_REMOTE_MANAGER_ENABLED"))

    # Redis operations:

    @cached_property
    def redis_client(self):
        """Redis client object (StrictRedis)"""
        return get_strict_redis()

    def _redis_call(self, method_name, args, description):
        """Wrapper over Redis client method call"""
        if self.enabled:
            try:
                from redis import ConnectionError
            except ImportError:
                raise MissingDependency(
                    "Unable to import redis. "
                    "CronRemoteManager requires this dependency."
                )
            try:
                method = getattr(self.redis_client, method_name)
                result = method(*args)
            except ConnectionError as error:
                self.logger.warning(
                    "Remote Manager: {} FAILED: {}".format(description, error)
                )
                result = None
            else:
                self.logger.info(
                    "Remote Manager: {} OK: {}".format(description, result)
                )
        else:
            self.logger.warning(
                "Remote Manager: {} CANCELLED: "
                "disabled in configuration".format(description)
            )
            result = None
        return result

    def redis_set(self, key, value):
        """Sets key's value in Redis"""
        return self._redis_call(
            "set", (key, value), "SET {}={}".format(key, value)
        )

    def redis_get(self, key):
        """Retrieves key's value from Redis"""
        return self._redis_call("get", (key,), "GET {}".format(key))

    def redis_delete(self, key):
        """Removes key from Redis"""
        return self._redis_call("delete", (key,), "DEL {}".format(key))

    def redis_rpush(self, key, value):
        """Appends value to the list on given key in Redis"""
        return self._redis_call(
            "rpush", (key, value), "RPUSH {} {}".format(key, value)
        )

    def redis_lpop(self, key):
        """Pops first element from list on given key in Redis"""
        return self._redis_call("lpop", (key,), "LPOP {}".format(key))

    # Redis keys:

    def get_status_key(self, host_name=None):
        """Creates Cron Scheduler status key from host name"""
        return self.STATUS_KEY.format(host_name=host_name or self.host_name)

    def get_kill_key(self, host_name=None):
        """Creates Cron Scheduler kill command key from host name"""
        return self.KILL_KEY.format(host_name=host_name or self.host_name)

    # Cron Scheduler status operations:

    def set_status(self, status, host_name=None):
        """Sets Cron Scheduler status"""
        return self.redis_set(self.get_status_key(host_name=host_name), status)

    def get_status(self, host_name=None):
        """Retrieves Cron Scheduler status"""
        return self.redis_get(self.get_status_key(host_name=host_name))

    def clear_status(self, host_name=None):
        """Removes Cron Scheduler status"""
        return self.redis_delete(self.get_status_key(host_name=host_name))

    def pop_status(self, host_name=None):
        """Retrieves and removes Cron Scheduler status"""
        status = self.get_status(host_name=host_name)
        if status is not None:
            self.clear_status(host_name=host_name)
        return status

    # Cron Scheduler kill command operations:

    def pop_killed(self, host_name=None):
        """Pops all cron jobs to be killed"""
        key = self.get_kill_key(host_name=host_name)
        job_specs = set()
        for i in range(self.MAX_KILLS):
            job_spec = self.redis_lpop(key)
            if job_spec:
                job_specs.add(job_spec)
            else:
                break
        return job_specs

    def kill(self, job_spec, host_name=None):
        """Ask the scheduler to kill a cron job of given job_spec"""
        return self.redis_rpush(
            self.get_kill_key(host_name=host_name), job_spec
        )

    # Shortcuts:

    def disable(self, host_name=None):
        """Ask the scheduler to disable itself and kill running workers"""
        return self.set_status(
            status=CronSchedulerStatus.DISABLED, host_name=host_name
        )

    def enable(self, host_name=None):
        """Ask the scheduler to enable itself and resume killed workers"""
        return self.set_status(
            status=CronSchedulerStatus.ENABLED, host_name=host_name
        )
