# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

from cronman.job import BaseCronJob
from cronman.models import CronTask
from cronman.taxonomies import PIDStatus
from cronman.utils import cron_jobs_module_config
from cronman.worker import CronWorker


class CleanCronTasks(BaseCronJob):
    """Changes status of dead CronTasks from STARTED to FAILED."""

    cronitor_id = "M21GXY"

    def __init__(self, logger=None):
        super(CleanCronTasks, self).__init__(logger=logger)
        self.cron_worker = CronWorker()
        self.cron_worker.logger = self.logger

    def run(self):
        """Main logic"""
        num_failed = 0
        cron_tasks = self.get_started_cron_tasks()
        if cron_tasks:
            active_pids = self.get_active_pids()
            for cron_task in cron_tasks:
                if cron_task.pid not in active_pids:
                    cron_task.mark_as_failed()
                    num_failed += 1
        if num_failed:
            status_message = "{} CronTask(s) marked as failed.".format(
                num_failed
            )
        else:
            status_message = "No CronTasks marked as failed."
        self.logger.info(status_message)

    def get_started_cron_tasks(self):
        """Retrieves started CronTasks"""
        allowed_tasks = cron_jobs_module_config(
            "ALLOWED_CRON_TASKS", default=()
        )
        return CronTask.objects.started().filter(cron_job__in=allowed_tasks)

    def get_active_pids(self):
        """Retrieves list of all active cron worker PIDs"""
        current_cron_jobs = self.cron_worker.get_worker_pid_list().status()[0]
        return [
            item["pid"]
            for item in current_cron_jobs
            if item["status"] == PIDStatus.ALIVE
        ]


class MotoCleanCronTasks(CleanCronTasks):
    """Changes status of dead CronTasks from STARTED to FAILED.

    Moto-specific cron job.
    """

    cronitor_id = "K7OpxI"
