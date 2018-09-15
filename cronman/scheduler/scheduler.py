# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import datetime
import logging

from django.utils.functional import cached_property

from croniter import croniter

from cronman.base import BaseCronObject
from cronman.exceptions import (
    CronSchedulerLocked,
    CronSchedulerNoJobs,
    CronSchedulerUnlocked,
)
from cronman.monitor import send_errors_to_sentry
from cronman.remote_manager import CronRemoteManager
from cronman.scheduler.files import (
    CronSchedulerLockFile,
    CronSchedulerResumeFile,
)
from cronman.spawner import CronSpawner
from cronman.taxonomies import CronSchedulerStatus
from cronman.utils import cron_jobs_module_config
from cronman.worker import CronWorker

logger = logging.getLogger("cronman.command.cron_scheduler")


class CronScheduler(BaseCronObject):
    """Cron Scheduler class.

    Responsible for:
    * determining which jobs should be started in given moment,
    * starting worker processes,
    * maintaining own lock.
    """

    interval = 2  # number of seconds between each scheduler call
    wait_for_memory = 7  # number of seconds to wait on first OOM error

    def __init__(self, now=None, **kwargs):
        kwargs["logger"] = kwargs.get("logger", logger)
        super(CronScheduler, self).__init__(**kwargs)
        self.now = now or datetime.datetime.now()
        self.lock_file = CronSchedulerLockFile(self.data_dir)
        self.resume_file = CronSchedulerResumeFile(self.data_dir)
        self.remote_manager = CronRemoteManager()

    @cached_property
    def cron_jobs(self):
        """Return jobs if CRONMAN_JOBS_MODULE is a valid module (must have
        CRON_JOBS attribute). Return () otherwise.
        """
        return cron_jobs_module_config("CRON_JOBS", default=())

    @cached_property
    def cron_spawner(self):
        """Cron Spawner instance"""
        return CronSpawner(
            data_dir=self.data_dir, debug=self.debug, logger=self.logger
        )

    @cached_property
    def cron_worker(self):
        """Cron Worker instance"""
        return CronWorker(
            data_dir=self.data_dir, debug=self.debug, logger=self.logger
        )

    @send_errors_to_sentry
    def run(self):
        """Starts worker processes for jobs that should start in this moment"""

        if not self.cron_jobs:
            self.warning(
                CronSchedulerNoJobs(
                    "Scheduler has no jobs to start. "
                    "Please verify settings.CRONMAN_JOBS_MODULE."
                )
            )

        killed_jobs = self.remote_manager.pop_killed()
        for job_spec_or_pid in killed_jobs:
            self.logger.info(
                'Scheduler: processing KILL "{}" request from '
                "Remote Manager...".format(job_spec_or_pid)
            )
            kill_output = self.cron_worker.kill(job_spec_or_pid)
            self.logger.info(kill_output)

        remote_status = (
            # Retrieve global (per-cluster) status:
            self.remote_manager.get_status("ALL")
            or
            # Retrieve per-host status and remove it from the queue:
            self.remote_manager.pop_status()
        )

        if self.lock_file.exists():
            if remote_status == CronSchedulerStatus.ENABLED:
                self.logger.info(
                    "Scheduler: processing ENABLE request from "
                    "Remote Manager..."
                )
                # Enable the scheduler, create resume file:
                self.enable(workers=True)
            else:
                return self.warning(
                    CronSchedulerLocked(
                        "Scheduler is disabled (lock file exists). "
                        "To enable it again, please run "
                        '"cron_scheduler enable". Quitting now.'
                    )
                )
        else:
            if remote_status == CronSchedulerStatus.DISABLED:
                self.logger.info(
                    "Scheduler: processing DISABLE request from "
                    "Remote Manager..."
                )
                # Disable scheduler, kill running workers, quit:
                return self.disable(workers=True)

        if self.resume_file.exists():
            self.resume_file.delete()
            output = self.resume_workers()
        else:
            output = ""

        run_start = datetime.datetime.now()
        jobs = self.get_jobs()
        num_jobs = len(jobs)
        num_started = 0
        for i, (time_spec, job_spec) in enumerate(jobs, 1):
            self.logger.info(
                "Starting worker for {} {} ({}/{})".format(
                    time_spec, job_spec, i, num_jobs
                )
            )
            pid = self.start_worker(job_spec)
            if pid is not None:
                num_started += 1
        run_end = datetime.datetime.now()
        if num_started:
            output += "Started {} job(s) in {}\n".format(
                num_started, run_end - run_start
            )
        else:
            output += "No jobs started.\n"
        return output

    @send_errors_to_sentry
    def disable(self, workers=False):
        """Disables the scheduler, so future calls to `run` will not start any
        workers. When `workers` option is set, it also kills all running
        workers via `CronWorker.suspend`.
        """
        if self.lock_file.exists():
            return self.warning(
                CronSchedulerLocked(
                    "Scheduler is already disabled (lock file exists)."
                )
            )
        self.lock_file.create()
        summary = ["lock file created"]

        if workers:
            suspend_output = self.cron_worker.suspend()
            summary.append("workers suspended")
        else:
            suspend_output = ""

        return "Scheduler disabled ({}).\n{}".format(
            ", ".join(summary), suspend_output
        )

    @send_errors_to_sentry
    def enable(self, workers=False):
        """Enables the scheduler, so future calls to `run` may start new
        workers. When `workers` option is set, it also creates a resume file,
        so next call to `run` will also start killed workers via
        `CronWorker.resume`.
        """
        if not self.lock_file.exists():
            return self.warning(
                CronSchedulerUnlocked(
                    "Scheduler is already enabled (lock file does not exist)."
                )
            )
        summary = []

        if workers:
            self.resume_file.create()
            summary.append("resume file created")

        self.lock_file.delete()
        summary.append("lock file deleted")

        return "Scheduler enabled ({}).\n".format(", ".join(summary))

    # Helpers:

    def get_datetime_range(self):
        """Start and end datetime for current scheduler call"""
        start = self.now.replace(second=0, microsecond=0) - datetime.timedelta(
            seconds=1
        )
        end = start + datetime.timedelta(minutes=self.interval)
        return start, end

    def get_jobs(self):
        """List of tuples (time spec, job spec) for jobs that should be started
        in current scheduler call.
        Jobs are sorted by start datetime, earliest first.
        """
        start, end = self.get_datetime_range()
        to_be_started = []
        for time_spec, job_spec in self.cron_jobs:
            job_start = croniter(time_spec, start).get_next(datetime.datetime)
            if job_start <= end:
                to_be_started.append((job_start, time_spec, job_spec))
        return [
            (time_spec, job_spec)
            for _job_start, time_spec, job_spec in sorted(to_be_started)
        ]

    def start_worker(self, job_spec):
        """Starts a worker process for given job spec"""
        return self.cron_spawner.start_worker(job_spec)

    def resume_workers(self):
        """Resumes killed workers"""
        return self.cron_worker.resume()
