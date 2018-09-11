# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import os


class BaseCronSchedulerFile(object):
    """Base class for Cron Scheduler file wrappers"""

    name = None  # must be set in subclass

    def __init__(self, data_dir):
        self.path = os.path.join(data_dir, self.name)

    def create(self):
        """Creates the lock file"""
        open(self.path, "w").close()

    def delete(self):
        """Deletes the lock file"""
        os.unlink(self.path)

    def exists(self):
        """Checks if the lock file exists"""
        return os.path.exists(self.path)


class CronSchedulerLockFile(BaseCronSchedulerFile):
    """Lock file for Cron Scheduler"""

    name = "scheduler.lock"


class CronSchedulerResumeFile(BaseCronSchedulerFile):
    """Resume file for Cron Scheduler"""

    name = "scheduler.resume"
