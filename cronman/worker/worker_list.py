# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import logging
import time
from collections import OrderedDict

from cronman.exceptions import PIDAccessError
from cronman.taxonomies import JobSpecStatus, PIDStatus
from cronman.utils import format_exception, parse_job_spec
from cronman.worker.worker_file import CronWorkerJobSpecFile, CronWorkerPIDFile

logger = logging.getLogger("cronman.command.cron_worker")


class BaseCronWorkerList(object):
    """Listing Cron Worker processes - base class"""

    file_class = None  # must be set in subclass

    def __init__(
        self,
        data_dir,
        job_spec=None,
        name=None,
        args=None,
        kwargs=None,
        pid=None,
    ):
        if pid:
            file_by_pid = self.file_class.by_pid(data_dir, pid)
            files = [file_by_pid] if file_by_pid else []
        else:
            if job_spec:
                name, args, kwargs = parse_job_spec(job_spec)
            # Files sorted by name:
            files = sorted(
                self.file_class.all(data_dir, name, args, kwargs),
                key=lambda pf: pf.name,
            )
        self.data_dir = data_dir
        self.files = files
        self.logger = logger


class CronWorkerPIDList(BaseCronWorkerList):
    """Listing and killing Cron Worker processes through PID files"""

    file_class = CronWorkerPIDFile
    wait_to_kill = 7

    def _iter_status_items(self):
        """Iterator over status information dicts extracted from files"""
        for pid_file in self.files:
            pid = pid_file.pid
            process_exists = pid_file.process.exists()
            if process_exists is None:
                error = PIDAccessError(
                    "{} No access to PID {}!".format(pid_file.name, pid)
                )
                self.logger.warning(format_exception(error))
                continue
            if process_exists:
                status = PIDStatus.ALIVE
            else:
                status = PIDStatus.DEAD
            item = OrderedDict()
            item["name"] = pid_file.name
            item["status"] = status
            item["pid"] = pid
            item["_pid_file"] = pid_file
            yield item

    def status(self):
        """Retrieves status information about listed PID files"""
        items = []
        totals = OrderedDict()
        totals["TOTAL"] = 0
        totals[PIDStatus.ALIVE] = 0
        totals[PIDStatus.DEAD] = 0
        for item in self._iter_status_items():
            totals[item["status"]] += 1
            totals["TOTAL"] += 1
            items.append(item)
        return items, totals

    def clean(self):
        """Removes dead PID files"""
        items = []
        totals = OrderedDict()
        totals["TOTAL"] = 0
        for item in self._iter_status_items():
            if item["status"] == PIDStatus.DEAD:
                item["_pid_file"].delete()
                item["status"] = PIDStatus.DELETED
            else:
                continue
            totals["TOTAL"] += 1
            items.append(item)
        return items, totals

    def kill(self):
        """Kills Cron Worker processes associated with listed PID files"""
        items = []
        totals = OrderedDict()
        totals["TOTAL"] = 0
        totals[PIDStatus.DEAD] = 0
        totals[PIDStatus.TERMED] = 0
        totals[PIDStatus.KILLED] = 0
        # Round 1: TERMINATE
        at_least_one_termed = False
        for item in self._iter_status_items():
            if item["status"] == PIDStatus.ALIVE:
                item["_pid_file"].process.terminate()
                item["status"] = PIDStatus.TERMED
                at_least_one_termed = True
            items.append(item)
        # Round 2: wait and KILL:
        if at_least_one_termed:
            wait = True
            for item in items:
                if (
                    item["status"] == PIDStatus.TERMED
                    and item["_pid_file"].process.alive()
                ):
                    # Sleep only once, before first kill:
                    if wait:
                        time.sleep(self.wait_to_kill)
                        wait = False
                        # Skip if process finished while we were sleeping:
                        if not item["_pid_file"].process.alive():
                            continue
                    item["_pid_file"].process.kill()
                    item["status"] = PIDStatus.KILLED
        # Update totals:
        for item in items:
            totals[item["status"]] += 1
            totals["TOTAL"] += 1
        return items, totals


class CronWorkerJobSpecList(BaseCronWorkerList):
    """Listing and resuming Cron Worker processes through JobSpec files"""

    file_class = CronWorkerJobSpecFile

    def _iter_status_items(self):
        """Iterator over status information dicts extracted from files"""
        for job_spec_file in self.files:
            pid_file = job_spec_file.pid_file
            if pid_file.exists():
                process_exists = pid_file.process.exists()
                if process_exists is None:
                    error = PIDAccessError(
                        "{} No access to PID {}!".format(
                            pid_file.name, pid_file.pid
                        )
                    )
                    self.logger.warning(format_exception(error))
                    continue
                if process_exists:
                    status = JobSpecStatus.ACTIVE
                else:
                    status = JobSpecStatus.STALLED
            else:
                status = JobSpecStatus.STALLED
            item = OrderedDict()
            item["name"] = job_spec_file.name
            item["status"] = status
            item["job_spec"] = job_spec_file.job_spec
            item["_job_spec_file"] = job_spec_file
            yield item

    def status(self):
        """Retrieves status information about listed JobSpec files"""
        items = []
        totals = OrderedDict()
        totals["TOTAL"] = 0
        totals[JobSpecStatus.ACTIVE] = 0
        totals[JobSpecStatus.STALLED] = 0
        for item in self._iter_status_items():
            totals[item["status"]] += 1
            totals["TOTAL"] += 1
            items.append(item)
        return items, totals

    def clean(self):
        """Removes stalled JobSpec files"""
        items = []
        totals = OrderedDict()
        totals["TOTAL"] = 0
        for item in self._iter_status_items():
            if item["status"] == JobSpecStatus.STALLED:
                item["_job_spec_file"].delete()
                item["status"] = JobSpecStatus.DELETED
            else:
                continue
            totals["TOTAL"] += 1
            items.append(item)
        return items, totals

    def resume(self):
        """Starts Cron Worker process for each stalled JobSpec file (resume)"""
        items = []
        totals = OrderedDict()
        totals["TOTAL"] = 0
        for item in self._iter_status_items():
            if item["status"] == JobSpecStatus.STALLED:
                pid = item["_job_spec_file"].resume()  # file gets deleted
                if pid is None:
                    continue
                item["status"] = JobSpecStatus.RESUMED
            else:
                continue
            totals["TOTAL"] += 1
            items.append(item)
        return items, totals
