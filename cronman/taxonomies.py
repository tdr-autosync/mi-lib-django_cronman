# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals


class LockType(object):
    """Type of lock acquired by Worker"""

    CLASS = "class"  # one lock per CronJob class
    PARAMS = "params"  # one lock per CronJob class + hash of params


class PIDStatus(object):
    """Status of PID file and associated process"""

    ALIVE = "ALIVE"  # PID file exists and corresponding process is alive
    DEAD = "DEAD"  # PID file exists but there is no corresponding process
    TERMED = "TERMED"  # Killed by SIGTERM
    KILLED = "KILLED"  # Killed by SIGKILL
    DELETED = "DELETED"  # PID file has been deleted


class JobSpecStatus(object):
    """Status of JobSpec file and associated process"""

    STALLED = "STALLED"  # JobSpec file exists and process is dead
    ACTIVE = "ACTIVE"  # JobSpec file exists and process is alive
    DELETED = "DELETED"  # JobSpec file has been deleted
    RESUMED = "RESUMED"  # Process has been started (resumed)


class CronTaskStatus(object):
    """Status of a Cron Task object"""

    WAITING = "waiting"
    QUEUED = "queued"
    STARTED = "started"
    FINISHED = "finished"
    FAILED = "failed"

    CHOICES = (
        (WAITING, "Waiting"),
        (QUEUED, "Queued"),
        (STARTED, "Started"),
        (FINISHED, "Finished"),
        (FAILED, "Failed"),
    )


class CPUPriority(object):
    """CPU Priority of Worker process (`nice`)"""

    LOWEST = 19
    LOW = 10
    NORMAL = 0  # Explicit default value
    # NOTE: higher priority values may require root access to be set
    # HIGH = -10
    # HIGHEST = -20


class IOPriority(object):
    """IO Priority of Worker process (`ionice`)"""

    IDLE = (3, None)  # Receives IO access only when devices are free

    # Best effort - regular IO priority:
    BEST_EFFORT_LOWEST = (2, 7)  # equivalent of `nice -n 19`
    BEST_EFFORT_LOW = (2, 6)  # equivalent of `nice -n 10`
    BEST_EFFORT_NORMAL = (2, 4)  # equivalent of `nice -n 0` (default)
    BEST_EFFORT_HIGH = (2, 2)  # equivalent of `nice -n -10`
    BEST_EFFORT_HIGHEST = (2, 0)  # equivalent of `nice -n -20`

    # Real time - process will ALWAYS receive IO access:
    # NOTE: these options are potentially dangerous
    # REAL_TIME_LOWEST = (1, 7)
    # REAL_TIME_LOW = (1, 6)
    # REAL_TIME_NORMAL = (1, 4)
    # REAL_TIME_HIGH = (1, 2)
    # REAL_TIME_HIGHEST = (1, 0)


class CronSchedulerStatus(object):
    """Cron Scheduler status choices"""

    DISABLED = "disabled"
    ENABLED = "enabled"
