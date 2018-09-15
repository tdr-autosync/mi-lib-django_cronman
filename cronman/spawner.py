# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import errno
import os
import sys
import time

from cronman.base import BaseCronObject
from cronman.config import app_settings
from cronman.job import cron_job_registry
from cronman.utils import bool_param, config, parse_job_spec, spawn


class CronSpawner(BaseCronObject):
    """Cron Spawner class - responsible for starting new worker processes"""

    wait_for_memory = 7  # number of seconds to wait on first OOM error

    def __init__(self, extra_env=None, **kwargs):
        super(CronSpawner, self).__init__(**kwargs)
        self.extra_env = extra_env or {}
        self.memory_error_occurred = False

    def get_worker_env(self):
        """Constructs a dictionary of environment variables for worker
        subprocess.
        This way we can ensure that cron-specific settings are identical
        for scheduler and workers.
        """

        # Note: We need to ensure that values stored in env are
        # string or bytestring

        environ = os.environ.copy()
        environ["CRONMAN_JOBS_MODULE"] = str(config("CRONMAN_JOBS_MODULE"))
        environ["CRONMAN_DATA_DIR"] = str(self.data_dir)
        environ["CRONMAN_DEBUG"] = str(
            int(bool_param(config("CRONMAN_DEBUG"), default=False))
        )
        environ["CRONMAN_NICE_CMD"] = str(config("CRONMAN_NICE_CMD") or "")
        environ["CRONMAN_IONICE_CMD"] = str(config("CRONMAN_IONICE_CMD") or "")
        environ["CRONMAN_CRONITOR_URL"] = str(config("CRONMAN_CRONITOR_URL"))
        environ["CRONMAN_CRONITOR_ENABLED"] = str(
            int(bool_param(config("CRONMAN_CRONITOR_ENABLED"), default=False))
        )
        environ["CRONMAN_SLACK_ENABLED"] = str(
            int(bool_param(config("CRONMAN_SLACK_ENABLED"), default=False))
        )
        environ["CRONMAN_SENTRY_ENABLED"] = str(
            int(bool_param(config("CRONMAN_SENTRY_ENABLED"), default=False))
        )
        environ.update(self.extra_env)
        return environ

    def get_process_priority_args(self, job_spec):
        """Constructs a list of arguments to be prepended to process args
        in order to assign CPU/IO priority.
        """
        cron_job_class = cron_job_registry.get(parse_job_spec(job_spec)[0])
        if (
            app_settings.CRONMAN_NICE_CMD
            and cron_job_class.worker_cpu_priority is not None
        ):
            cpu_priority_args = [
                app_settings.CRONMAN_NICE_CMD,
                "-n",
                str(cron_job_class.worker_cpu_priority),
            ]
        else:
            cpu_priority_args = []
        if (
            app_settings.CRONMAN_IONICE_CMD
            and cron_job_class.worker_io_priority is not None
        ):
            io_class, io_class_data = cron_job_class.worker_io_priority
            io_priority_args = [
                app_settings.CRONMAN_IONICE_CMD,
                "-c",
                str(io_class),
            ]
            if io_class_data is not None:
                io_priority_args += ["-n", str(io_class_data)]
        else:
            io_priority_args = []
        return cpu_priority_args + io_priority_args

    def start_worker(self, job_spec):
        """Starts a worker process for given job spec"""
        # Building process parameters:
        kwargs = {"env": self.get_worker_env()}
        args = [sys.executable, sys.argv[0], "cron_worker", "run", job_spec]
        options = [a for a in sys.argv if a.startswith("--settings=")]
        if self.sentry.raven_cmd:
            # All worker processes should be executed by raven-cmd:
            args[-1] = args[-1].replace('"', "'")
            args = self.get_process_priority_args(job_spec) + args + options
            args = [('"{}"'.format(a) if " " in a else a) for a in args]
            args = [self.sentry.raven_cmd, "-c", " ".join(args)]
        else:
            args = self.get_process_priority_args(job_spec) + args + options
        # Spawning a new subprocess
        # (with special case for temporary memory error):
        pid = None
        tries = 1 if self.memory_error_occurred else 2
        while tries:
            tries -= 1
            try:
                pid = spawn(*args, **kwargs)
            except OSError as error:
                if error.errno != errno.ENOMEM:
                    raise
                self.memory_error_occurred = True
                if tries:
                    self.logger.debug(
                        "Unable to start a worker process "
                        "for {} due to Out-Of-Memory error."
                        "Retrying in {} seconds...".format(
                            job_spec, self.wait_for_memory
                        )
                    )
                    time.sleep(self.wait_for_memory)
                else:
                    self.warning(
                        RuntimeError(
                            "Unable to start a worker process "
                            "for {} due to Out-Of-Memory error.".format(
                                job_spec
                            )
                        )
                    )
                    break
            else:
                break
        return pid
