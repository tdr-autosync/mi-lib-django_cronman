# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

from django.db import connections
from django.utils import timezone
from django.utils.functional import cached_property

from cronman.job import BaseCronJob
from cronman.models import CronTask
from cronman.spawner import CronSpawner
from cronman.utils import cron_jobs_module_config


class RunCronTasks(BaseCronJob):
    """Starts worker processes for cron jobs requested to run in Admin
    via CronTask model.
    """

    lock_ignore_errors = True
    cronitor_id = "zg9G1G"

    @cached_property
    def cron_spawner(self):
        """Cron Spawner instance"""
        return CronSpawner(logger=self.logger)

    def run(self):
        """Main logic"""
        cron_tasks = self.get_pending_cron_tasks()
        num_cron_tasks = len(cron_tasks)
        num_started = 0
        for i, cron_task in enumerate(cron_tasks, 1):
            self.logger.info(
                "Starting worker for CronTask {} ({}/{})".format(
                    cron_task, i, num_cron_tasks
                )
            )
            pid = self.start_cron_task(cron_task)
            if pid is not None:
                num_started += 1
        if num_started:
            status_message = "Started {} CronTask(s).".format(num_started)
        else:
            status_message = "No CronTasks started."
        self.logger.info(status_message)

    def get_pending_cron_tasks(self):
        """Retrieve pending CronTasks"""
        allowed_tasks = cron_jobs_module_config(
            "ALLOWED_CRON_TASKS", default=()
        )
        cron_tasks = list(
            CronTask.objects.pending()
            .filter(start_at__lte=timezone.now())
            .filter(cron_job__in=allowed_tasks)
        )
        connections.close_all()  # close db connections
        return cron_tasks

    def start_cron_task(self, cron_task):
        """Starts worker for given CronTask"""
        return self.cron_spawner.start_worker(cron_task.job_spec())


class MotoRunCronTasks(RunCronTasks):
    """Starts worker processes for cron jobs requested to run in Admin
    via CronTask model.

    Moto-specific cron job.
    """

    cronitor_id = "t6bp0e"
