# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import os
import time

from django.utils.encoding import force_bytes

from cronman.job import BaseCronJob
from cronman.taxonomies import CPUPriority, IOPriority, LockType

# Test cron jobs:


class Sleep(BaseCronJob):
    """Test CronJob: sleeps for given number of seconds.
    No lock - concurrent calls allowed.
    """

    lock_type = None  # concurrency allowed
    can_resume = False

    def run(self, seconds=None, path=None, **kwargs):
        """Main logic"""
        time.sleep(int(seconds) if seconds else 0)
        if path:
            with open(path, "wb") as file_:
                kwargs["seconds"] = seconds or ""
                kwargs["path"] = path or ""
                for key, value in kwargs.items():
                    file_.write(force_bytes("{}={}\n".format(key, value)))
                for key, value in os.environ.items():
                    file_.write(force_bytes("{}={}\n".format(key, value)))
                file_.write(
                    force_bytes("Slept for {} second(s).\n".format(seconds))
                )
                file_.write(b"Done.\n")


class ClassLockedSleep(Sleep):
    """Test CronJob: sleeps for given number of seconds.
    Lock by class - concurrent calls of this class are no allowed.
    """

    lock_type = LockType.CLASS


class ParamsLockedSleep(Sleep):
    """Test CronJob: sleeps for given number of seconds.
    Lock by params - concurrent calls of this class are allowed only if
    they use different arguments.
    """

    lock_type = LockType.PARAMS


class IgnoreLockErrorsSleep(Sleep):
    """Test CronJob: sleeps for given number of seconds.
    Ignore lock errors - report lock errors as warnings.
    Lock by params - concurrent calls of this class are allowed only if
    they use different arguments.
    """

    lock_type = LockType.PARAMS
    lock_ignore_errors = True


class SlackNotifyDoneSleep(Sleep):
    """Test CronJob: sleeps for given number of seconds.
    Slack notification is sent by the worker when job is done.
    """

    slack_notify_done = True


class LowCPUSleep(Sleep):
    """Test CronJob: sleeps for given number of seconds.
    Low CPU priority (`nice -n 10`)
    """

    worker_cpu_priority = CPUPriority.LOW


class LowestCPUIOSleep(Sleep):
    """Test CronJob: sleeps for given number of seconds.
    Lowest CPU and IO priority (`nice -n 19 ionice -c 2 -n 7`)

    NOTE: This is just an example, in real life there is no need to set
    `IOPriority.BEST_EFFORT_LOWEST` when `CPUPriority.LOWEST` is set because
    this IO priority level is implied.
    """

    worker_cpu_priority = CPUPriority.LOWEST
    worker_io_priority = IOPriority.BEST_EFFORT_LOWEST


class IdleIOSleep(Sleep):
    """Test CronJob: sleeps for given number of seconds.
    Idle IO priority.
    """

    worker_io_priority = IOPriority.IDLE


class PersistentSleep(Sleep):
    """Test CronJob: sleeps for given number of seconds.
    Has resume capability.
    """

    lock_type = LockType.CLASS
    can_resume = True


class PersistentSleep2(Sleep):
    """Test CronJob: sleeps for given number of seconds.
    Has resume capability. (2)
    """

    lock_type = LockType.PARAMS
    can_resume = True
