# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import logging
import re
import sys
import time
import traceback

from django.utils import timezone

from cronman.base import BaseCronObject
from cronman.exceptions import (
    CronJobNotRegistered,
    CronTaskInvalidStatus,
    CronWorkerInvalidParams,
    CronWorkerLocked,
)
from cronman.job import cron_job_registry
from cronman.models import CronTask
from cronman.monitor import send_errors_to_sentry
from cronman.taxonomies import LockType
from cronman.utils import TabularFormatter, format_exception, parse_job_spec
from cronman.worker.cron_job_info import CronJobClassList
from cronman.worker.process_manager import ProcessManager
from cronman.worker.signal_notifier import SignalNotifier
from cronman.worker.worker_file import CronWorkerPIDFile
from cronman.worker.worker_list import CronWorkerJobSpecList, CronWorkerPIDList

logger = logging.getLogger("cronman.command.cron_worker")


class CronWorker(BaseCronObject):
    """Cron Worker class.

    Responsible for:
    * running a CronJob class defined by job spec,
    * passing status to external logging services,
    * maintaining pidfile / lock,
    * listing active worker processes,
    * killing processes.
    """

    NO_PID_FILES_MESSAGE = "No PID file(s) found."
    NO_JOB_SPEC_FILES_MESSAGE = "No JobSpec file(s) found."
    NO_CRON_JOBS_MESSAGE = "No cron job(s) found."

    def __init__(self, **kwargs):
        self.cronitor_id = None
        self.formatter = TabularFormatter()
        kwargs["logger"] = kwargs.get("logger", logger)
        super(CronWorker, self).__init__(**kwargs)

    @staticmethod
    def get_cronitor_id(kwargs):
        """Retrieves Cronitor ID passed through cron job params,
        removes it from the params.
        """
        return (kwargs or {}).pop("cronitor_id", None)

    @send_errors_to_sentry
    def run(self, job_spec):
        """Executes logic defined in CronJob class specified by `job_spec`"""
        name, args, kwargs, cron_job_class = self.parse_job_spec_with_class(
            job_spec
        )
        self.cronitor_id = self.get_cronitor_id(kwargs)
        cron_task = self.get_cron_task(kwargs)
        if cron_task and not cron_task.is_pending():
            if self.cron_task_killed(cron_task):
                self.logger.info(
                    'Starting "{}" for killed CronTask.'.format(job_spec)
                )
            else:
                error = CronTaskInvalidStatus(
                    'Unable to start "{}", because associated CronTask '
                    'has invalid status "{}".'.format(
                        job_spec, cron_task.get_status_display()
                    )
                )
                return self.warning(error)

        if cron_task:
            cron_task.mark_as_queued()

        pid_file = self.get_pid_file(cron_job_class, name, args, kwargs)
        if self.pid_file_locked(pid_file, cron_job_class.lock_check_attempts):
            error = CronWorkerLocked(
                'Unable to start "{}", because similar process '
                "is already running (PID file exists).".format(job_spec)
            )
            return self.warning(
                error, silent=cron_job_class.lock_ignore_errors
            )
        job_spec_file = self.get_job_spec_file(cron_job_class, pid_file)

        with SignalNotifier(job_spec):

            pid_file.create()
            if job_spec_file:
                job_spec_file.create(job_spec)

            run_start = timezone.now()
            if cron_task:
                cron_task.mark_as_started(pid_file.pid, run_start)
            self.logger.info('Starting "{}"...'.format(job_spec))

            ok = self.run_cron_job(job_spec, cron_job_class, args, kwargs)

            run_end = timezone.now()
            duration = run_end - run_start
            if ok:
                if cron_task:
                    cron_task.mark_as_finished(run_end)
                self.logger.info(
                    'Processing "{}" finished after {}'.format(
                        job_spec, duration
                    )
                )
            else:
                if cron_task:
                    cron_task.mark_as_failed()
                self.logger.warning(
                    'Processing "{}" FAILED after {}'.format(
                        job_spec, duration
                    )
                )

            if job_spec_file:
                job_spec_file.delete()
            pid_file.delete()

        return "{}: Processed {}".format("OK" if ok else "FAIL", job_spec)

    @send_errors_to_sentry
    def status(self, job_spec_or_pid=None):
        """Shows status of all running worker processes,
        optionally filtered by job_spec or PID
        """
        worker_pid_list = self.get_worker_pid_list(job_spec_or_pid)
        items, totals = worker_pid_list.status()
        return self.formatter.format_listing_output(
            items,
            totals=totals,
            title="STATUS:",
            empty_message=self.NO_PID_FILES_MESSAGE,
        )

    def _kill(self, job_spec_or_pid=None):
        """Kills all worker processes,
        optionally filtered by job_spec or PID
        """
        worker_pid_list = self.get_worker_pid_list(job_spec_or_pid)
        items, totals = worker_pid_list.kill()
        return self.formatter.format_listing_output(
            items,
            totals=totals,
            title="KILL:",
            empty_message=self.NO_PID_FILES_MESSAGE,
        )

    kill = send_errors_to_sentry(_kill)

    def _clean_pid_files(self):
        """Removes all dead PID files"""
        items, totals = self.get_worker_pid_list().clean()
        return self.formatter.format_listing_output(
            items,
            totals=totals,
            title="CLEAN PID FILES:",
            empty_message=self.NO_PID_FILES_MESSAGE,
        )

    def _clean_job_spec_files(self):
        """Removes all stalled JobSpec files"""
        items, totals = self.get_worker_job_spec_list().clean()
        return self.formatter.format_listing_output(
            items,
            totals=totals,
            title="CLEAN JOBSPEC FILES:",
            empty_message=self.NO_JOB_SPEC_FILES_MESSAGE,
        )

    def _clean(self):
        """Removes all dead PID files and stalled JobSpec files"""
        return self._clean_pid_files() + self._clean_job_spec_files()

    clean = send_errors_to_sentry(_clean)

    @send_errors_to_sentry
    def suspend(self):
        """Shortcut command to get:
        1. `clean` - remove all DEAD PID files and STALLED JobSpec files
        2. `kill` - kill ALL running worker processes.
        Returns joined output of called commands.
        """
        return self._clean() + self._kill()

    @send_errors_to_sentry
    def resume(self, job_spec_or_pid=None):
        """Starts all previously killed worker processes with `can_resume`
        capability,
        optionally filtered by job_spec or PID
        """
        worker_job_spec_list = self.get_worker_job_spec_list(job_spec_or_pid)
        items, totals = worker_job_spec_list.resume()
        return self.formatter.format_listing_output(
            items,
            totals=totals,
            title="RESUME:",
            empty_message=self.NO_JOB_SPEC_FILES_MESSAGE,
        )

    @send_errors_to_sentry
    def info(self, name=None):
        """Shows a list of all available cron job class,
        or if name is provided, show its parameters and docstring
        """
        name, cron_job_class = self.parse_job_spec_with_class(name)[::3]
        cron_job_list = CronJobClassList(
            name=name, cron_job_class=cron_job_class
        )
        if name:
            items, totals = cron_job_list.details()[0], None
            vertical = True
        else:
            items, totals = cron_job_list.summary()
            vertical = False
        return self.formatter.format_listing_output(
            items,
            totals=totals,
            vertical=vertical,
            empty_message=self.NO_CRON_JOBS_MESSAGE,
        )

    # Cron Job running internals:

    def run_cron_job(self, job_spec, cron_job_class, args, kwargs):
        """Initializes and runs a CronJob"""
        self.before_start(job_spec, cron_job_class, args, kwargs)
        try:
            results = cron_job_class().run(*args, **kwargs)
        except Exception as e:
            self.on_error(job_spec, cron_job_class, args, kwargs, e)
            ok = False
        else:
            self.on_success(job_spec, cron_job_class, args, kwargs, results)
            ok = True
        return ok

    def before_start(self, job_spec, cron_job_class, args, kwargs):
        """Notifies monitor services when job is about to start"""
        cronitor_id = self.cronitor_id or cron_job_class.cronitor_id
        if cronitor_id and cron_job_class.cronitor_ping_run:
            self.cronitor.run(cronitor_id)

    def on_success(self, job_spec, cron_job_class, args, kwargs, result):
        """Notifies monitor services when job succeeded"""
        cronitor_id = self.cronitor_id or cron_job_class.cronitor_id
        if cronitor_id:
            self.cronitor.complete(cronitor_id)
        if cron_job_class.slack_notify_done:
            self.slack.post('Cron job "{}" is done.'.format(job_spec))

    def on_error(self, job_spec, cron_job_class, args, kwargs, error):
        """Notifies monitor services when job failed"""
        cronitor_id = self.cronitor_id or cron_job_class.cronitor_id
        message = format_exception(error)
        self.logger.error(message)
        self.sentry.capture_exception()
        if cronitor_id and cron_job_class.cronitor_ping_fail:
            self.cronitor.fail(cronitor_id, msg=message)
        if self.debug:
            traceback.print_exc(file=sys.stderr)

    # Helpers:

    @staticmethod
    def get_cron_task(kwargs):
        """Retrieves CronTask by ID passed through cron job params.
        Removes CronTask ID from params.
        """
        cron_task_id = (kwargs or {}).pop(CronTask.TASK_ID_PARAM, None)
        if cron_task_id:
            cron_task = CronTask.objects.filter(pk=cron_task_id).first()
        else:
            cron_task = None
        return cron_task

    @staticmethod
    def cron_task_killed(cron_task):
        """Checks if given Cron Task is in killed state
        (status STARTED + inactive PID).
        """
        return (
            cron_task.is_started()
            and cron_task.pid
            and not ProcessManager(cron_task.pid).alive()
        )

    def get_pid_file(self, cron_job_class, name, args, kwargs):
        """Retrieves PID file for given CronJob and its parameters"""
        name = cron_job_class.lock_name or name
        if cron_job_class.lock_type == LockType.CLASS:
            pid_file_name = CronWorkerPIDFile.get_file_name(name)
        elif cron_job_class.lock_type == LockType.PARAMS:
            pid_file_name = CronWorkerPIDFile.get_file_name(name, args, kwargs)
        else:  # No lock, just PID file
            pid_file_name = CronWorkerPIDFile.get_file_name(
                name, args, kwargs, random=True
            )
        return CronWorkerPIDFile(self.data_dir, pid_file_name)

    def get_job_spec_file(self, cron_job_class, pid_file):
        """Retrieves JobSpec file for given CronJob class and PIDFile"""
        return pid_file.job_spec_file if cron_job_class.can_resume else None

    @staticmethod
    def pid_file_locked(pid_file, lock_check_attempts):
        """Checks if given PIDFile exists and belongs to running process"""
        locked = True
        while lock_check_attempts > 0:
            lock_check_attempts -= 1
            locked = pid_file.exists_with_alive_process()
            if not locked:
                break
            elif lock_check_attempts:
                time.sleep(1)
        return locked

    def get_worker_pid_list(self, job_spec_or_pid=None):
        """Retrieves CronWorkerPIDList instance"""
        name, args, kwargs, pid = self.parse_job_spec_or_pid(job_spec_or_pid)
        return CronWorkerPIDList(
            self.data_dir, name=name, args=args, kwargs=kwargs, pid=pid
        )

    def get_worker_job_spec_list(self, job_spec_or_pid=None):
        """Retrieves CronWorkerJobSpecList instance"""
        name, args, kwargs, pid = self.parse_job_spec_or_pid(job_spec_or_pid)
        return CronWorkerJobSpecList(
            self.data_dir, name=name, args=args, kwargs=kwargs, pid=pid
        )

    @staticmethod
    def parse_job_spec_with_class(job_spec=None):
        """Converts a string (job spec) into quadruple
        (name, args, kwargs, cron_job_class).
        Raises CronWorkerInvalidParams if string cannot be parsed or
        there is no cron job class for given specification.
        """
        if job_spec:
            try:
                name, args, kwargs = parse_job_spec(job_spec)
                cron_job_class = cron_job_registry.get(name)
            except (ValueError, CronJobNotRegistered) as error:
                raise CronWorkerInvalidParams(format_exception(error))
        else:
            name = args = kwargs = cron_job_class = None
        return name, args, kwargs, cron_job_class

    @staticmethod
    def parse_job_spec_or_pid(job_spec_or_pid=None):
        """Converts a string (job spec or integer - PID) into quadruple
        (name, args, kwargs, pid).
        Raises CronWorkerInvalidParams if string cannot be parsed.
        """
        if job_spec_or_pid:
            if re.match("\d+", job_spec_or_pid):
                pid = int(job_spec_or_pid)
                name = args = kwargs = None
            else:
                pid = None
                try:
                    name, args, kwargs = parse_job_spec(job_spec_or_pid)
                except ValueError as error:
                    raise CronWorkerInvalidParams(format_exception(error))
        else:
            name = args = kwargs = pid = None
        return name, args, kwargs, pid
