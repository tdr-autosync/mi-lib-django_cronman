# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import errno
import hashlib
import os
import shutil
import signal

from django.test.testcases import TestCase
from django.test.utils import override_settings
from django.utils.encoding import force_bytes

import mock

from cronman.config import app_settings
from cronman.worker import CronWorker


TEMP_FILE = "/tmp/sleep.txt"
TEST_CRONMAN_DATA_DIR = os.path.join(app_settings.CRONMAN_DATA_DIR, "test")


def override_cron_settings(**kwargs):
    """Override settings with default values for `cronman` app"""
    defaults = {
        "CRONMAN_DATA_DIR": TEST_CRONMAN_DATA_DIR,
        "CRONMAN_DEBUG": True,
        "CRONMAN_JOBS_MODULE": "cronman.tests.cron_jobs",
        "CRONMAN_CRONITOR_ENABLED": False,
        "CRONMAN_SLACK_ENABLED": False,
        "CRONMAN_SENTRY_ENABLED": True,
        "CRONMAN_RAVEN_CMD": None,
        "CRONMAN_NICE_CMD": "nice",
        "CRONMAN_IONICE_CMD": "ionice",
        "CRONMAN_REMOTE_MANAGER_ENABLED": False,
    }
    defaults.update(kwargs)
    return override_settings(**defaults)


def create_pid_file(job_spec, pid=None):
    """Utility function to create PID file for given job spec"""
    pid = os.getpid() if pid is None else pid
    worker = CronWorker()
    name, args, kwargs, cron_job_class = worker.parse_job_spec_with_class(
        job_spec
    )
    pid_file = worker.get_pid_file(cron_job_class, name, args, kwargs)
    with mock.patch("cronman.worker.worker_file.os.getpid", lambda: pid):
        pid_file.create()
    return pid_file


def create_job_spec_file(job_spec, content=None):
    """Utility function to create JobSpec file for given job spec"""
    content = job_spec if content is None else content
    worker = CronWorker()
    name, args, kwargs, cron_job_class = worker.parse_job_spec_with_class(
        job_spec
    )
    pid_file = worker.get_pid_file(cron_job_class, name, args, kwargs)
    job_spec_file = pid_file.job_spec_file
    job_spec_file.create(content)
    return job_spec_file


def get_params_hash(args, kwargs):
    """Generate shortened hash of cron job parameters."""
    params_bytes_repr = force_bytes(repr((args, kwargs)))
    return hashlib.md5(params_bytes_repr).hexdigest()[:10]


def patch_ps(active_pids=(), zombie_pids=()):
    """Patches `ps` calls made by ProcessManager"""

    def mock_check_output(*args, **kwargs):
        pid = int(args[0][2])
        if pid in active_pids:
            status = "R"
        elif pid in zombie_pids:
            status = "Z"
        else:
            status = ""
        return "{}\n".format(status)

    return mock.patch(
        "cronman.worker.process_manager.subprocess.check_output",
        mock_check_output,
    )


def patch_kill(active_pids=(), die_on_sigterm_pids=(), die_on_sigkill_pids=()):
    """Patches `os.kill` calls made by ProcessManager"""

    active_pids = list(active_pids)  # this have to be mutable

    def mock_kill(pid, sig):
        if pid not in active_pids:
            raise OSError(errno.ESRCH, "No such process")
        if sig == signal.SIGTERM and pid in die_on_sigterm_pids:
            active_pids.remove(pid)
        if sig == signal.SIGKILL and pid in die_on_sigkill_pids:
            active_pids.remove(pid)

    return mock.patch("cronman.worker.process_manager.os.kill", mock_kill)


def mock_environ():
    """Mock for `os.environ.copy`"""
    return {"SOME_ENV_VAR": "42"}


def expected_worker_env():
    """Environment dictionary expected to be passed to worker subprocess"""
    cronitor_url = "https://cronitor.link/{cronitor_id}/{end_point}"
    return {
        "SOME_ENV_VAR": "42",
        "CRONMAN_CRONITOR_ENABLED": "0",
        "CRONMAN_CRONITOR_URL": cronitor_url,
        "CRONMAN_JOBS_MODULE": "cronman.tests.cron_jobs",
        "CRONMAN_DATA_DIR": TEST_CRONMAN_DATA_DIR,
        "CRONMAN_DEBUG": "1",
        "CRONMAN_SLACK_ENABLED": "0",
        "CRONMAN_NICE_CMD": "nice",
        "CRONMAN_IONICE_CMD": "ionice",
        "CRONMAN_SENTRY_ENABLED": "1",
    }


class BaseCronTestCase(TestCase):
    """Base class for `cron_*` commands test cases"""

    def setUp(self):
        super(BaseCronTestCase, self).setUp()
        self._remove_temp_file()
        self._remove_test_cron_data_dir()

    def tearDown(self):
        self._remove_temp_file()
        self._remove_test_cron_data_dir()
        super(BaseCronTestCase, self).tearDown()

    def _remove_temp_file(self):
        if os.path.exists(TEMP_FILE):
            os.unlink(TEMP_FILE)

    def _remove_test_cron_data_dir(self):
        if os.path.exists(TEST_CRONMAN_DATA_DIR):
            shutil.rmtree(TEST_CRONMAN_DATA_DIR)

    def assertMessageInTempFile(self, message):
        """Check that the message is present in TEMP_FILE"""
        self.assertTrue(os.path.exists(TEMP_FILE))
        with open(TEMP_FILE, "r") as file_:
            lines = [line.strip() for line in file_.readlines()]
        self.assertIn(message, lines)
