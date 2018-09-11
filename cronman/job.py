# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import logging

from cronman.exceptions import CronJobAlreadyRegistered, CronJobNotRegistered
from cronman.taxonomies import LockType


class CronJobRegistry(object):
    """Collection of all CronJob classes referenced by name"""

    def __init__(self):
        self._registry = {}

    def register(self, cron_job_class, name=None):
        """Adds a new CronJob class to the registry"""
        name = name or cron_job_class.__name__
        if name in self._registry:
            raise CronJobAlreadyRegistered(name)
        self._registry[name] = cron_job_class

    def unregister(self, name=None, cron_job_class=None):
        """Removes a CronJob class from the registry"""
        name = name or cron_job_class.__name__
        if name not in self._registry:
            raise CronJobNotRegistered(name)
        del self._registry[name]

    def get(self, name):
        """Retrieves a CronJob class from the registry"""
        if name not in self._registry:
            raise CronJobNotRegistered(name)
        return self._registry[name]

    def items(self):
        """Retrieves all registered items"""
        return self._registry.items()


cron_job_registry = CronJobRegistry()


class BaseCronJob(object):
    """Base class for CronJobs"""

    lock_type = LockType.CLASS
    lock_name = None  # May be used to override job name for lock
    lock_check_attempts = 1  # Number of lock check attempts
    lock_ignore_errors = False  # Should we consider lock errors as warnings?
    cronitor_id = None
    cronitor_ping_run = True  # Should we ping Cronitor when job started?
    cronitor_ping_fail = True  # Should we ping Cronitor when job failed?
    slack_notify_done = False  # Post to Slack when job's done?
    worker_cpu_priority = None  # CPU priority for worker processes
    worker_io_priority = None  # IO priority for worker processes
    can_resume = True  # Can we resume this job after suspension?

    def __init__(self, logger=None):
        self.logger = logger or logging.getLogger(
            "cronman.command.{}".format(self.__module__.split(".")[-1])
        )

    def run(self, *args, **kwargs):
        """Main logic"""
        raise NotImplementedError()  # Put your logic here
