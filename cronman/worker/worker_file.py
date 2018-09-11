# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import hashlib
import os

from django.utils.encoding import force_bytes, force_text
from django.utils.functional import cached_property

from cronman.spawner import CronSpawner
from cronman.worker.process_manager import ProcessManager


class BaseCronWorkerFile(object):
    """Stats file kept by Cron Worker - base class"""

    EXTENSION = None  # must be set in subclass

    def __init__(self, data_dir, name):
        self.name = name
        self.data_dir = data_dir
        self.path = os.path.join(
            self.data_dir, "{}{}".format(self.name, self.EXTENSION)
        )

    @classmethod
    def get_file_name(cls, name, args=None, kwargs=None, random=False):
        """Generates file name from CronJob's name, args and kwargs"""
        parts = [name]
        if args or kwargs:
            params_bytes_repr = force_bytes(repr((args, kwargs)))
            parts.append(hashlib.md5(params_bytes_repr).hexdigest()[:10])
        if random:
            parts.append(hashlib.md5(os.urandom(16)).hexdigest()[:10])
        return "_".join(parts)

    @classmethod
    def all(cls, data_dir, name=None, args=None, kwargs=None):
        """Iterates over files in given directory"""
        for file_name in os.listdir(data_dir):
            base_name, ext = os.path.splitext(file_name)
            if ext == cls.EXTENSION:
                if name:  # Filter files by specific job:
                    base_name_begin = cls.get_file_name(name, args, kwargs)
                    if base_name.startswith(base_name_begin):
                        yield cls(data_dir, base_name)
                else:  # No filters:
                    yield cls(data_dir, base_name)

    def write_content(self, content):
        """Populates this file with new content"""
        with open(self.path, "wb") as file_:
            file_.write(force_bytes(content))
            file_.flush()
            # NOTE:
            # "flush() does not necessarily write the file’s data to disk.
            # Use flush() followed by os.fsync() to ensure this behavior."
            # (from Python 2.7 docs)
            os.fsync(file_.fileno())

    def read_content(self):
        """Reads contents of this file"""
        try:
            with open(self.path, "rb") as file_:
                content = force_text(file_.read())
        except IOError:  # File deleted already
            content = None
        return content

    def delete(self):
        """Deletes this file"""
        try:
            os.unlink(self.path)
        except OSError:
            pass  # File deleted already

    def exists(self):
        """Checks if this file exists"""
        return os.path.exists(self.path)


class CronWorkerPIDFile(BaseCronWorkerFile):
    """PID file (and lock) for Cron Worker"""

    EXTENSION = ".pid"

    @classmethod
    def by_pid(cls, data_dir, pid):
        """Retrieves PID file from given directory by PID value"""
        for candidate_pid_file in cls.all(data_dir):
            if candidate_pid_file.pid == pid:
                pid_file = candidate_pid_file
                break
        else:
            pid_file = None
        return pid_file

    def create(self):
        """Creates the PID file"""
        pid = os.getpid()
        self.write_content(pid)
        self.__dict__["pid"] = pid  # Bypass `pid` property

    @cached_property
    def pid(self):
        """PID extracted from this file"""
        try:
            pid = int(self.read_content())
        except (ValueError, TypeError):  # PID file deleted / truncated
            pid = None
        return pid

    @cached_property
    def process(self):
        """Process Manager instance for this PID file"""
        return ProcessManager(self.pid)  # ProcessManager can handle `None`

    def exists_with_alive_process(self):
        """Checks if PID file exists and corresponding process is alive.
        Removes file if process is dead.
        """
        if self.exists():
            if not self.pid or self.process.alive() is False:
                # PID file deleted/truncated or process is dead:
                self.delete()
                result = False
            else:  # Process is alive or we don't have access:
                result = True
        else:
            result = False
        return result

    @cached_property
    def job_spec_file(self):
        """JobSpec file associated with this file"""
        return CronWorkerJobSpecFile(self.data_dir, self.name)


class CronWorkerJobSpecFile(BaseCronWorkerFile):
    """JobSpec file for Cron Worker's running jobs with resume feature"""

    EXTENSION = ".jobspec"

    @classmethod
    def by_pid(cls, data_dir, pid):
        """Retrieves JobSpec file from given directory by PID value"""
        job_spec_file = None
        pid_file = CronWorkerPIDFile.by_pid(data_dir, pid)
        if pid_file:
            job_spec_file = cls(data_dir, pid_file.name)
            if not job_spec_file.exists():
                job_spec_file = None
        return job_spec_file

    def create(self, job_spec):
        """Creates the JobSpec file"""
        self.write_content(job_spec)
        self.__dict__["job_spec"] = job_spec  # Bypass `job_spec` property

    def resume(self):
        """Starts a worker process for job spec stored in this file"""
        job_spec = self.job_spec
        self.delete()  # file is deleted before spawning new worker
        if job_spec:
            pid = self.cron_spawner.start_worker(job_spec)
        else:
            pid = None
        return pid

    @cached_property
    def job_spec(self):
        """JobSpec extracted from this file"""
        return self.read_content() or None

    @cached_property
    def pid_file(self):
        """PID file associated with this file"""
        return CronWorkerPIDFile(self.data_dir, self.name)

    @cached_property
    def cron_spawner(self):
        """Cron Spawner instance"""
        return CronSpawner(
            data_dir=self.data_dir, extra_env={"CRON_PROCESS_RESUMED": "1"}
        )
