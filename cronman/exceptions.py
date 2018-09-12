# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

from django.core.management import CommandError

# General errors:


class MissingDependency(ImportError):
    """Exception raised when missing optional dependency is accessed."""


# CronJobRegistry errors:


class CronJobRegistryError(KeyError):
    """Error related to CronJobRegistry"""


class CronJobAlreadyRegistered(CronJobRegistryError):
    """CronJob class of given name is already registered"""


class CronJobNotRegistered(CronJobRegistryError):
    """CronJob class of given name is not registered"""


# CronScheduler errors:


class CronSchedulerError(CommandError):
    """General CronScheduler error"""


class CronSchedulerLocked(CronSchedulerError):
    """CronScheduler is locked"""


class CronSchedulerUnlocked(CronSchedulerError):
    """CronScheduler is unlocked"""


class CronSchedulerNoJobs(CronSchedulerError):
    """CronScheduler no jobs to start"""


# CronWorker errors:


class CronWorkerError(CommandError):
    """General CronScheduler error"""


class PIDAccessError(CronWorkerError):
    """CronWorker has no access to process by PID"""


class CronTaskInvalidStatus(CronWorkerError):
    """CronWorker received CronTask with improper status"""


class CronWorkerLocked(CronWorkerError):
    """CronWorker cannot start due to active lock"""


class CronWorkerInvalidParams(CronWorkerError):
    """CronWorker received invalid arguments"""
