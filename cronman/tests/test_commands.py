# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import os
import socket

from django.core.management import CommandError, call_command

import mock
import redis

from cronman.config import app_settings
from cronman.scheduler import CronScheduler
from cronman.taxonomies import CronSchedulerStatus
from cronman.tests.base import (
    TEMP_FILE,
    BaseCronTestCase,
    create_job_spec_file,
    create_pid_file,
    get_params_hash,
    override_cron_settings,
    patch_kill,
    patch_ps,
)
from cronman.tests.cron_jobs import CRON_JOBS
from cronman.tests.tools import call_worker
from cronman.worker import CronWorkerPIDFile, ProcessManager


class SchedulerCommandTestCase(BaseCronTestCase):
    """Tests for `cron_scheduler` command"""

    @override_cron_settings()
    @mock.patch("cronman.scheduler.scheduler.CronSpawner.start_worker")
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    def test_run_worker_process(self, mock_cron_worker, mock_start):
        """Test for running scheduler which starts one worker for each entry in
        CRONMAN_JOBS_MODULE.
        """
        output = call_command("cron_scheduler", "run") or ""
        self.assertIn("Started {} job(s)".format(len(CRON_JOBS)), output)
        mock_start.assert_has_calls(
            [
                mock.call("Sleep:seconds=1,path={}".format(TEMP_FILE)),
                mock.call("Sleep:seconds=2"),
            ]
        )
        mock_cron_worker.return_value.resume.assert_not_called()

    @override_cron_settings(CRONMAN_JOBS_MODULE=None)
    @mock.patch("cronman.scheduler.scheduler.CronSpawner.start_worker")
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    def test_run_no_worker_processes(self, mock_cron_worker, mock_start):
        """Test for running scheduler when there are no worker processes
        to be started
        """
        output = call_command("cron_scheduler", "run") or ""
        self.assertIn("No jobs started.", output)
        mock_start.assert_not_called()
        mock_cron_worker.return_value.resume.assert_not_called()

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=True)
    @mock.patch("cronman.scheduler.scheduler.CronSpawner.start_worker")
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_run_disabled_remotely(
        self, mock_redis, mock_cron_worker, mock_start
    ):
        """Test for running scheduler when disable request has been sent
        through Remote Manager.
        """

        def redis_get(key, *args, **kwargs):
            """Return CronSchedulerStatus.DISABLED for current host only."""
            if key == "cron_scheduler:status:{}".format(socket.gethostname()):
                value = CronSchedulerStatus.DISABLED
            else:
                value = None
            return value

        mock_redis.return_value.get.side_effect = redis_get
        mock_redis.return_value.lpop.return_value = None  # No remote KILL
        output = call_command("cron_scheduler", "run") or ""
        # Result should match "disable --workers":
        self.assertIn(
            "Scheduler disabled (lock file created, workers suspended).",
            output,
        )
        mock_cron_worker.return_value.suspend.assert_called_once()
        mock_redis.return_value.delete.assert_called_once()

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=True)
    @mock.patch("cronman.scheduler.scheduler.CronSpawner.start_worker")
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_run_enabled_remotely(
        self, mock_redis, mock_cron_worker, mock_start
    ):
        """Test for running scheduler when enable request has been sent
        through Remote Manager.
        """

        def redis_get(key, *args, **kwargs):
            """Return CronSchedulerStatus.ENABLED for current host only."""
            if key == "cron_scheduler:status:{}".format(socket.gethostname()):
                value = CronSchedulerStatus.ENABLED
            else:
                value = None
            return value

        mock_redis.return_value.get.side_effect = redis_get
        mock_redis.return_value.lpop.return_value = None  # No remote KILL
        mock_cron_worker.return_value.resume.return_value = "<resume output>"

        scheduler = CronScheduler()
        scheduler.resume_file.create()

        output = call_command("cron_scheduler", "run") or ""

        self.assertIn("Started {} job(s)".format(len(CRON_JOBS)), output)
        mock_start.assert_has_calls(
            [
                mock.call("Sleep:seconds=1,path={}".format(TEMP_FILE)),
                mock.call("Sleep:seconds=2"),
            ]
        )
        mock_cron_worker.return_value.resume.assert_called_once()
        mock_redis.return_value.delete.assert_called_once()

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=True)
    @mock.patch("cronman.scheduler.scheduler.CronSpawner.start_worker")
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_run_kill_requested_remotely(
        self, mock_redis, mock_cron_worker, mock_start
    ):
        """Test for running scheduler when kill request has been sent
        through Remote Manager.
        """
        return_values = ["ParseInvoiceData"]

        def mock_lpop(key):
            try:
                return return_values.pop()
            except IndexError:
                return None

        mock_redis.return_value.lpop.side_effect = mock_lpop
        output = call_command("cron_scheduler", "run") or ""
        self.assertIn("Started {} job(s)".format(len(CRON_JOBS)), output)
        mock_start.assert_has_calls(
            [
                mock.call("Sleep:seconds=1,path={}".format(TEMP_FILE)),
                mock.call("Sleep:seconds=2"),
            ]
        )
        mock_cron_worker.return_value.kill.assert_called_once_with(
            "ParseInvoiceData"
        )

    @override_cron_settings()
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    def test_disable(self, mock_cron_worker):
        """Test for disabling scheduler"""
        output = call_command("cron_scheduler", "disable") or ""
        self.assertIn("Scheduler disabled (lock file created).", output)
        mock_cron_worker.return_value.suspend.assert_not_called()

    @override_cron_settings()
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    def test_disable_with_workers(self, mock_cron_worker):
        """Test for disabling scheduler with workers option"""
        output = call_command("cron_scheduler", "disable", workers=True) or ""
        self.assertIn(
            "Scheduler disabled (lock file created, workers suspended).",
            output,
        )
        mock_cron_worker.return_value.suspend.assert_called_once()

    @override_cron_settings()
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    def test_disable_already_disabled(self, mock_cron_worker):
        """Test for disabling scheduler when it was disabled already"""
        call_command("cron_scheduler", "disable")
        output = call_command("cron_scheduler", "disable")
        self.assertIn(
            "CronSchedulerLocked: "
            "Scheduler is already disabled (lock file exists).",
            output,
        )
        mock_cron_worker.return_value.suspend.assert_not_called()

    @override_cron_settings()
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    def test_disable_and_run(self, mock_cron_worker):
        """Test for attempt to run disabled scheduler"""
        call_command("cron_scheduler", "disable")
        output = call_command("cron_scheduler", "run")
        self.assertIn(
            "CronSchedulerLocked: "
            "Scheduler is disabled (lock file exists). "
            'To enable it again, please run "cron_scheduler enable". '
            "Quitting now.",
            output,
        )
        mock_cron_worker.return_value.suspend.assert_not_called()
        mock_cron_worker.return_value.resume.assert_not_called()

    @override_cron_settings()
    def test_enable(self):
        """Test for enabling scheduler"""
        call_command("cron_scheduler", "disable")
        output = call_command("cron_scheduler", "enable") or ""
        self.assertIn("Scheduler enabled (lock file deleted).", output)

    @override_cron_settings()
    def test_enable_with_workers(self):
        """Test for enabling scheduler with workers option"""
        call_command("cron_scheduler", "disable")
        output = call_command("cron_scheduler", "enable", workers=True) or ""
        self.assertIn(
            "Scheduler enabled (resume file created, lock file deleted).",
            output,
        )

    @override_cron_settings()
    def test_enable_already_enabled(self):
        """Test for enabling scheduler when it was enabled already"""
        output = call_command("cron_scheduler", "enable")
        self.assertEqual(
            output,
            "CronSchedulerUnlocked: "
            "Scheduler is already enabled (lock file does not exist).\n",
        )

    @override_cron_settings(CRONMAN_JOBS_MODULE=None)
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    def test_disable_enable_and_run(self, mock_cron_worker):
        """Test for running scheduler after disabling and enabling it again"""
        call_command("cron_scheduler", "disable")
        call_command("cron_scheduler", "enable")
        output = call_command("cron_scheduler", "run") or ""
        self.assertIn("No jobs started.", output)
        mock_cron_worker.return_value.suspend.assert_not_called()
        mock_cron_worker.return_value.resume.assert_not_called()

    @override_cron_settings()
    def test_invalid_command_call_no_method(self):
        """Test for invalid scheduler command call: no method"""
        with self.assertRaises(CommandError):
            call_command("cron_scheduler")

    @override_cron_settings()
    def test_invalid_command_call_unknown_method(self):
        """Test for invalid scheduler command call: unknown method"""
        with self.assertRaises(CommandError):
            call_command("cron_scheduler", "foobar")


class WorkerCommandTestCase(BaseCronTestCase):
    """Tests for `cron_worker` command"""

    # RUN:

    @override_cron_settings()
    def test_run_worker_process_success(self):
        """Test for running worker - success"""
        job_spec = "Sleep:seconds=1,path={0}".format(TEMP_FILE)
        self.assertTrue(call_worker(job_spec).ok)
        # Check if worker process sent a message to output file:
        self.assertMessageInTempFile("Slept for 1 second(s).")

    @override_cron_settings()
    def test_run_worker_process_failure(self):
        """Test for running worker - failure"""
        # Error: "NaN" can't be converted to an integer:
        job_spec = "Sleep:seconds=NaN,path={0}".format(TEMP_FILE)
        self.assertFalse(call_worker(job_spec).ok)

    @override_cron_settings()
    def test_run_worker_process_with_complex_params(self):
        """Test for running worker with various types of parameters"""
        job_spec = (
            "Sleep:seconds=1,path={0},"
            'param_1=AAA,param_2=3.14,param_3="a b c"'.format(TEMP_FILE)
        )
        self.assertTrue(call_worker(job_spec).ok)
        # Check if worker process sent a message to output file:
        self.assertMessageInTempFile("param_1=AAA")
        self.assertMessageInTempFile("param_2=3.14")
        self.assertMessageInTempFile("param_3=a b c")  # quotes removed

    @override_cron_settings()
    def test_run_worker_no_lock_enabled_success(self):
        """Test for running worker while other worker is on, but no lock
        is acquired - success.
        """
        running_job_spec = "Sleep:seconds=10"
        job_spec = "Sleep:seconds=1"
        pid = 1001
        create_pid_file(running_job_spec, pid)
        with patch_ps(active_pids=[pid]):
            with patch_kill(active_pids=[pid]):
                self.assertTrue(call_worker(job_spec).ok)

    @override_cron_settings()
    def test_run_worker_class_lock_enabled_failure(self):
        """Test for attempt to run worker while CLASS-based lock is enabled -
        failure.
        """
        locked_job_spec = "ClassLockedSleep:seconds=10"
        job_spec = "ClassLockedSleep:seconds=1"  # same class, diff. params
        pid = 1001
        create_pid_file(locked_job_spec, pid)
        with patch_ps(active_pids=[pid]):
            with patch_kill(active_pids=[pid]):
                result = call_worker(job_spec)
        self.assertEqual(result.exc_class_name, "CronWorkerLocked")
        self.assertEqual(
            result.exc_message,
            'Unable to start "ClassLockedSleep:seconds=1", '
            "because similar process is already running (PID file exists).\n",
        )

    @override_cron_settings()
    def test_run_worker_params_lock_enabled_failure(self):
        """Test for attempt to run worker while PARAMS-based lock is enabled -
        failure.
        """
        locked_job_spec = "ParamsLockedSleep:seconds=10"
        job_spec = "ParamsLockedSleep:seconds=10"  # same class, same params
        pid = 1001
        create_pid_file(locked_job_spec, pid)
        with patch_ps(active_pids=[pid]):
            with patch_kill(active_pids=[pid]):
                result = call_worker(job_spec)
        self.assertEqual(result.exc_class_name, "CronWorkerLocked")
        self.assertEqual(
            result.exc_message,
            'Unable to start "ParamsLockedSleep:seconds=10", '
            "because similar process is already running (PID file exists).\n",
        )

    @override_cron_settings()
    def test_run_worker_params_lock_enabled_success(self):
        """Test for attempt to run worker while PARAMS-based lock is enabled -
        success.
        """
        locked_job_spec = "ParamsLockedSleep:seconds=10"
        job_spec = "ParamsLockedSleep:seconds=1"  # same class, diff. params
        pid = 1001
        create_pid_file(locked_job_spec, pid)
        with patch_ps(active_pids=[pid]):
            with patch_kill(active_pids=[pid]):
                self.assertTrue(call_worker(job_spec).ok)

    @override_cron_settings()
    def test_invalid_command_call_no_method(self):
        """Test for invalid worker command call: no method"""
        with self.assertRaises(CommandError):
            call_command("cron_worker")

    @override_cron_settings()
    def test_invalid_command_call_unknown_method(self):
        """Test for invalid worker command call: unknown method"""
        with self.assertRaises(CommandError):
            call_command("cron_worker", "foobar")

    # STATUS

    @override_cron_settings()
    @patch_ps()
    @patch_kill()
    def test_status_no_workers(self):
        """Test for listing active workers - 0 PID files"""
        output = call_command("cron_worker", "status")
        self.assertEqual(output, "STATUS:\nNo PID file(s) found.\n")

    @override_cron_settings()
    def test_status(self):
        """Test for listing active workers - 2 PID files with active workers"""
        pid_1, pid_2 = 1001, 1002
        hash_1 = get_params_hash([], {"seconds": "10"})
        create_pid_file("ParamsLockedSleep:seconds=10", pid_1)
        create_pid_file("ClassLockedSleep:seconds=10", pid_2)
        with patch_ps(active_pids=[pid_1, pid_2]):
            with patch_kill(active_pids=[pid_1, pid_2]):
                output = call_command("cron_worker", "status")
        self.assertEqual(
            output,
            "STATUS:\n"
            "ClassLockedSleep\tALIVE\t{pid_2}\n"
            "ParamsLockedSleep_{hash_1}\tALIVE\t{pid_1}\n"
            "TOTAL: 2\tALIVE: 2\tDEAD: 0\n".format(
                hash_1=hash_1, pid_1=pid_1, pid_2=pid_2
            ),
        )

    @override_cron_settings()
    def test_status_by_name(self):
        """Test for listing active workers by cron job name"""
        pid_1, pid_2 = 1001, 1002
        create_pid_file("ParamsLockedSleep:seconds=10", pid_1)
        create_pid_file("ClassLockedSleep:seconds=10", pid_2)
        with patch_ps(active_pids=[pid_1, pid_2]):
            with patch_kill(active_pids=[pid_1, pid_2]):
                output = call_command(
                    "cron_worker", "status", "ClassLockedSleep"
                )
        self.assertEqual(
            output,
            "STATUS:\n"
            "ClassLockedSleep\tALIVE\t{pid_2}\n"
            "TOTAL: 1\tALIVE: 1\tDEAD: 0\n".format(pid_2=pid_2),
        )

    @override_cron_settings()
    def test_status_by_pid(self):
        """Test for listing active workers by PID"""
        pid_1, pid_2 = 1001, 1002
        create_pid_file("ParamsLockedSleep:seconds=10", pid_1)
        create_pid_file("ClassLockedSleep:seconds=10", pid_2)
        with patch_ps(active_pids=[pid_1, pid_2]):
            with patch_kill(active_pids=[pid_1, pid_2]):
                output = call_command("cron_worker", "status", str(pid_2))
        self.assertEqual(
            output,
            "STATUS:\n"
            "ClassLockedSleep\tALIVE\t{pid_2}\n"
            "TOTAL: 1\tALIVE: 1\tDEAD: 0\n".format(pid_2=pid_2),
        )

    # KILL

    @override_cron_settings()
    @patch_ps()
    @patch_kill()
    def test_kill_no_workers(self):
        """Test for killing all active workers - 0 PID files"""
        output = call_command("cron_worker", "kill")
        self.assertEqual(output, "KILL:\nNo PID file(s) found.\n")

    @override_cron_settings()
    def test_kill_2_workers(self):
        """Test for killing all active workers - 2 processes terminated"""
        pid_1, pid_2 = 1001, 1002
        hash_1 = get_params_hash([], {"seconds": "10"})
        create_pid_file("ParamsLockedSleep:seconds=10", pid_1)
        create_pid_file("ClassLockedSleep:seconds=10", pid_2)
        with patch_ps(active_pids=[pid_1, pid_2]):
            with patch_kill(
                active_pids=[pid_1, pid_2], die_on_sigterm_pids=[pid_1, pid_2]
            ):
                output = call_command("cron_worker", "kill")
                self.assertEqual(
                    output,
                    "KILL:\n"
                    "ClassLockedSleep\tTERMED\t{pid_2}\n"
                    "ParamsLockedSleep_{hash_1}\tTERMED\t{pid_1}\n"
                    "TOTAL: 2\tDEAD: 0\tTERMED: 2\tKILLED: 0\n".format(
                        hash_1=hash_1, pid_1=pid_1, pid_2=pid_2
                    ),
                )
                self.assertFalse(ProcessManager(pid_1).alive())
                self.assertFalse(ProcessManager(pid_2).alive())

    @override_cron_settings()
    def test_kill_truncated_pidfile(self):
        """Test for killing all active workers - truncated PIDfile case"""
        hash_1 = get_params_hash([], {"seconds": "10"})
        create_pid_file("ParamsLockedSleep:seconds=10", "")  # empty file
        with patch_ps():
            with patch_kill():
                output = call_command("cron_worker", "kill")
                self.assertEqual(
                    output,
                    "KILL:\n"
                    "ParamsLockedSleep_{hash_1}\tDEAD\t{pid_1}\n"
                    "TOTAL: 1\tDEAD: 1\tTERMED: 0\tKILLED: 0\n".format(
                        hash_1=hash_1, pid_1=None
                    ),
                )
        # PIDFile should handle IOError (missing file) correctly:
        self.assertIsNone(
            CronWorkerPIDFile(app_settings.CRONMAN_DATA_DIR, "Fake").pid
        )
        # ProcessManager should handle missing PID
        # (due to truncated/missing file) correctly:
        process_manager = ProcessManager(None)
        self.assertFalse(process_manager.alive())
        self.assertEqual(process_manager.status(), "")

    @override_cron_settings()
    def test_kill_by_name(self):
        """Test for killing all active workers by cron job name"""
        pid_1, pid_2 = 1001, 1002
        create_pid_file("ParamsLockedSleep:seconds=10", pid_1)
        create_pid_file("ClassLockedSleep:seconds=10", pid_2)
        with patch_ps(active_pids=[pid_1, pid_2]):
            with patch_kill(
                active_pids=[pid_1, pid_2], die_on_sigterm_pids=[pid_2]
            ):
                output = call_command(
                    "cron_worker", "kill", "ClassLockedSleep"
                )
                self.assertEqual(
                    output,
                    "KILL:\n"
                    "ClassLockedSleep\tTERMED\t{pid_2}\n"
                    "TOTAL: 1\tDEAD: 0\tTERMED: 1\tKILLED: 0\n".format(
                        pid_2=pid_2
                    ),
                )
                self.assertTrue(ProcessManager(pid_1).alive())
                self.assertFalse(ProcessManager(pid_2).alive())

    @override_cron_settings()
    @patch_ps()
    @patch_kill()
    def test_kill_by_pid_no_worker(self):
        """Test for killing worker by PID - no PID file found"""
        output = call_command("cron_worker", "kill", "1125")
        self.assertEqual(output, "KILL:\nNo PID file(s) found.\n")

    @override_cron_settings()
    def test_kill_by_pid_existing_worker(self):
        """Test for killing worker by PID - 1 process terminated"""
        pid_1, pid_2 = 1001, 1002
        hash_1 = get_params_hash([], {"seconds": "10"})
        create_pid_file("ParamsLockedSleep:seconds=10", pid_1)
        create_pid_file("ClassLockedSleep:seconds=10", pid_2)
        with patch_ps(active_pids=[pid_1, pid_2]):
            with patch_kill(
                active_pids=[pid_1, pid_2], die_on_sigterm_pids=[pid_1]
            ):
                output = call_command("cron_worker", "kill", str(pid_1))
                self.assertEqual(
                    output,
                    "KILL:\n"
                    "ParamsLockedSleep_{hash_1}\tTERMED\t{pid_1}\n"
                    "TOTAL: 1\tDEAD: 0\tTERMED: 1\tKILLED: 0\n".format(
                        hash_1=hash_1, pid_1=pid_1
                    ),
                )
                self.assertFalse(ProcessManager(pid_1).alive())
                self.assertTrue(ProcessManager(pid_2).alive())

    # CLEAN

    @override_cron_settings()
    @patch_ps()
    @patch_kill()
    def test_clean_no_files(self):
        """Test for cleaning dead/stalled files - no files, no deletion"""
        output = call_command("cron_worker", "clean")
        self.assertEqual(
            output,
            "CLEAN PID FILES:\n"
            "No PID file(s) found.\n"
            "CLEAN JOBSPEC FILES:\n"
            "No JobSpec file(s) found.\n",
        )

    @override_cron_settings()
    def test_clean_all_files_active(self):
        """Test for cleaning dead/stalled files - all files active, no deletion
        """
        pid_1, pid_2, pid_3 = 1001, 1002, 1003
        pid_file_1 = create_pid_file("ParamsLockedSleep:seconds=10", pid_1)
        pid_file_2 = create_pid_file("ClassLockedSleep:seconds=10", pid_2)
        pid_file_3 = create_pid_file("PersistentSleep:seconds=30", pid_3)
        job_spec_file_3 = create_job_spec_file("PersistentSleep:seconds=30")
        with patch_ps(active_pids=[pid_1, pid_2, pid_3]):
            with patch_kill(
                active_pids=[pid_1, pid_2, pid_3],
                die_on_sigterm_pids=[pid_1, pid_2, pid_3],
            ):
                output = call_command("cron_worker", "clean")
                self.assertEqual(
                    output,
                    "CLEAN PID FILES:\n"
                    "No PID file(s) found.\n"
                    "CLEAN JOBSPEC FILES:\n"
                    "No JobSpec file(s) found.\n",
                )
                # No process killed on during cleaning:
                self.assertTrue(ProcessManager(pid_1).alive())
                self.assertTrue(ProcessManager(pid_2).alive())
                self.assertTrue(ProcessManager(pid_3).alive())
        # Files associated with active processes are not deleted:
        self.assertTrue(os.path.exists(pid_file_1.path))
        self.assertTrue(os.path.exists(pid_file_2.path))
        self.assertTrue(os.path.exists(pid_file_3.path))
        self.assertTrue(os.path.exists(job_spec_file_3.path))

    @override_cron_settings()
    def test_clean_3_dead_pids_1_stalled_jobspec(self):
        """Test for cleaning dead/stalled files - 3 dead PIDfiles,
        1 stalled JobSpec file
        """
        pid_2, pid_3 = 1002, 1003
        hash_1 = get_params_hash([], {"seconds": "10"})
        pid_file_1 = create_pid_file("ParamsLockedSleep:seconds=10", "")
        pid_file_2 = create_pid_file("ClassLockedSleep:seconds=10", pid_2)
        pid_file_3 = create_pid_file("PersistentSleep:seconds=30", pid_3)
        job_spec_file_3 = create_job_spec_file("PersistentSleep:seconds=30")
        with patch_ps():
            with patch_kill():
                output = call_command("cron_worker", "clean")
                self.assertEqual(
                    output,
                    "CLEAN PID FILES:\n"
                    "ClassLockedSleep\tDELETED\t{pid_2}\n"
                    "ParamsLockedSleep_{hash_1}\tDELETED\t{pid_1}\n"
                    "PersistentSleep\tDELETED\t{pid_3}\n"
                    "TOTAL: 3\n"
                    "CLEAN JOBSPEC FILES:\n"
                    "PersistentSleep\tDELETED\tPersistentSleep:seconds=30\n"
                    "TOTAL: 1\n".format(
                        hash_1=hash_1, pid_1=None, pid_2=pid_2, pid_3=pid_3
                    ),
                )
        # Files associated with already dead processes are deleted:
        self.assertFalse(os.path.exists(pid_file_1.path))
        self.assertFalse(os.path.exists(pid_file_2.path))
        self.assertFalse(os.path.exists(pid_file_3.path))
        self.assertFalse(os.path.exists(job_spec_file_3.path))

    # SUSPEND

    @override_cron_settings()
    @patch_ps()
    @patch_kill()
    def test_suspend_no_workers(self):
        """Test for suspending all active workers - 0 PID files"""
        output = call_command("cron_worker", "suspend")
        self.assertEqual(
            output,
            "CLEAN PID FILES:\n"
            "No PID file(s) found.\n"
            "CLEAN JOBSPEC FILES:\n"
            "No JobSpec file(s) found.\n"
            "KILL:\n"
            "No PID file(s) found.\n",
        )

    @override_cron_settings()
    def test_suspend_3_workers(self):
        """Test for suspending all active workers - 3 processes terminated, 1
        can be resumed.
        """
        pid_1, pid_2, pid_3 = 1001, 1002, 1003
        hash_1 = get_params_hash([], {"seconds": "10"})
        pid_file_1 = create_pid_file("ParamsLockedSleep:seconds=10", pid_1)
        pid_file_2 = create_pid_file("ClassLockedSleep:seconds=10", pid_2)
        pid_file_3 = create_pid_file("PersistentSleep:seconds=30", pid_3)
        job_spec_file_3 = create_job_spec_file("PersistentSleep:seconds=30")
        with patch_ps(active_pids=[pid_1, pid_2, pid_3]):
            with patch_kill(
                active_pids=[pid_1, pid_2, pid_3],
                die_on_sigterm_pids=[pid_1, pid_2, pid_3],
            ):
                output = call_command("cron_worker", "suspend")
                self.assertEqual(
                    output,
                    "CLEAN PID FILES:\n"
                    "No PID file(s) found.\n"
                    "CLEAN JOBSPEC FILES:\n"
                    "No JobSpec file(s) found.\n"
                    "KILL:\n"
                    "ClassLockedSleep\tTERMED\t{pid_2}\n"
                    "ParamsLockedSleep_{hash_1}\tTERMED\t{pid_1}\n"
                    "PersistentSleep\tTERMED\t1003\n"
                    "TOTAL: 3\tDEAD: 0\tTERMED: 3\tKILLED: 0\n".format(
                        hash_1=hash_1, pid_1=pid_1, pid_2=pid_2
                    ),
                )
                self.assertFalse(ProcessManager(pid_1).alive())
                self.assertFalse(ProcessManager(pid_2).alive())
                self.assertFalse(ProcessManager(pid_3).alive())
        # Files associated with killed processes are not deleted:
        self.assertTrue(os.path.exists(pid_file_1.path))
        self.assertTrue(os.path.exists(pid_file_2.path))
        self.assertTrue(os.path.exists(pid_file_3.path))
        self.assertTrue(os.path.exists(job_spec_file_3.path))

    @override_cron_settings()
    def test_suspend_cleaning(self):
        """Test for suspending all active workers - clearing dead PIDfiles
        before killing.
        """
        pid_2, pid_3 = 1002, 1003
        hash_1 = get_params_hash([], {"seconds": "10"})
        pid_file_1 = create_pid_file("ParamsLockedSleep:seconds=10", "")
        pid_file_2 = create_pid_file("ClassLockedSleep:seconds=10", pid_2)
        pid_file_3 = create_pid_file("PersistentSleep:seconds=30", pid_3)
        job_spec_file_3 = create_job_spec_file("PersistentSleep:seconds=30")
        with patch_ps():
            with patch_kill():
                output = call_command("cron_worker", "suspend")
                self.assertEqual(
                    output,
                    "CLEAN PID FILES:\n"
                    "ClassLockedSleep\tDELETED\t{pid_2}\n"
                    "ParamsLockedSleep_{hash_1}\tDELETED\t{pid_1}\n"
                    "PersistentSleep\tDELETED\t{pid_3}\n"
                    "TOTAL: 3\n"
                    "CLEAN JOBSPEC FILES:\n"
                    "PersistentSleep\tDELETED\tPersistentSleep:seconds=30\n"
                    "TOTAL: 1\n"
                    "KILL:\n"
                    "No PID file(s) found.\n".format(
                        hash_1=hash_1, pid_1=None, pid_2=pid_2, pid_3=pid_3
                    ),
                )
        # Files associated with already dead processes are deleted (clean):
        self.assertFalse(os.path.exists(pid_file_1.path))
        self.assertFalse(os.path.exists(pid_file_2.path))
        self.assertFalse(os.path.exists(pid_file_3.path))
        self.assertFalse(os.path.exists(job_spec_file_3.path))

    # RESUME

    @override_cron_settings()
    @patch_ps()
    @patch_kill()
    @mock.patch("cronman.worker.worker_file.CronSpawner.start_worker")
    def test_resume_no_files(self, mock_start):
        """Test for resuming workers - no JobSpec files"""
        output = call_command("cron_worker", "resume")
        self.assertEqual(output, "RESUME:\n" "No JobSpec file(s) found.\n")
        mock_start.assert_not_called()

    @override_cron_settings()
    @mock.patch("cronman.worker.worker_file.CronSpawner.start_worker")
    def test_resume_all_files_active(self, mock_start):
        """Test for resuming workers - all workers active, no resuming."""
        pid_1, pid_2, pid_3 = 1001, 1002, 1003
        create_pid_file("ParamsLockedSleep:seconds=10", pid_1)
        create_pid_file("PersistentSleep:seconds=20", pid_2)
        create_job_spec_file("PersistentSleep:seconds=20")
        create_pid_file("PersistentSleep2:seconds=30", pid_3)
        create_job_spec_file("PersistentSleep2:seconds=30")
        with patch_ps(active_pids=[pid_1, pid_2, pid_3]):
            with patch_kill(
                active_pids=[pid_1, pid_2, pid_3],
                die_on_sigterm_pids=[pid_1, pid_2, pid_3],
            ):
                output = call_command("cron_worker", "resume")
                self.assertEqual(
                    output, "RESUME:\n" "No JobSpec file(s) found.\n"
                )
        mock_start.assert_not_called()

    @override_cron_settings()
    @mock.patch("cronman.worker.worker_file.CronSpawner.start_worker")
    def test_resume_2_workers(self, mock_start):
        """Test for resuming workers - 2 workers resumed"""
        pid_1, pid_2, pid_3 = 1001, 1002, 1003
        hash_3 = get_params_hash([], {"seconds": "30"})
        create_pid_file("ParamsLockedSleep:seconds=10", pid_1)
        create_pid_file("PersistentSleep:seconds=20", pid_2)
        job_spec_file_2 = create_job_spec_file("PersistentSleep:seconds=20")
        create_pid_file("PersistentSleep2:seconds=30", pid_3)
        job_spec_file_3 = create_job_spec_file("PersistentSleep2:seconds=30")
        with patch_ps():
            with patch_kill():
                output = call_command("cron_worker", "resume")
                self.assertEqual(
                    output,
                    "RESUME:\n"
                    "PersistentSleep\tRESUMED\tPersistentSleep:seconds=20\n"
                    "PersistentSleep2_{hash_3}\tRESUMED\t"
                    "PersistentSleep2:seconds=30\n"
                    "TOTAL: 2\n".format(hash_3=hash_3),
                )
        # JobSpec files have been deleted before spawning new processes:
        self.assertFalse(os.path.exists(job_spec_file_2.path))
        self.assertFalse(os.path.exists(job_spec_file_3.path))
        # Processes have been spawned:
        mock_start.assert_has_calls(
            [
                mock.call("PersistentSleep:seconds=20"),
                mock.call("PersistentSleep2:seconds=30"),
            ]
        )

    @override_cron_settings()
    @mock.patch("cronman.worker.worker_file.CronSpawner.start_worker")
    def test_resume_truncated_jobspec_file(self, mock_start):
        """Test for resuming workers - truncated JobSpec file case
        (no resuming)."""
        create_pid_file("PersistentSleep:seconds=20", 1001)
        create_job_spec_file("PersistentSleep:seconds=20", "")
        with patch_ps():
            with patch_kill():
                output = call_command("cron_worker", "resume")
                self.assertEqual(
                    output, "RESUME:\n" "No JobSpec file(s) found.\n"
                )
        mock_start.assert_not_called()

    @override_cron_settings()
    @mock.patch("cronman.worker.worker_file.CronSpawner.start_worker")
    def test_resume_no_pid_file(self, mock_start):
        """Test for resuming workers - no PID file case (resuming OK)."""
        job_spec_file_1 = create_job_spec_file("PersistentSleep:seconds=20")
        with patch_ps():
            with patch_kill():
                output = call_command("cron_worker", "resume")
                self.assertEqual(
                    output,
                    "RESUME:\n"
                    "PersistentSleep\tRESUMED\tPersistentSleep:seconds=20\n"
                    "TOTAL: 1\n",
                )
        # JobSpec files have been deleted before spawning new processes:
        self.assertFalse(os.path.exists(job_spec_file_1.path))
        # Processes have been spawned:
        mock_start.assert_called_once_with("PersistentSleep:seconds=20")

    # INFO

    @override_cron_settings()
    def test_info(self):
        """Test for listing all available cron job classes"""
        output = call_command("cron_worker", "info")
        self.assertIn("Sleep\tcronman.cron_jobs.sleep.Sleep\n", output)

    @override_cron_settings()
    def test_info_summary(self):
        """Test for listing all available cron job classes"""
        output = call_command("cron_worker", "info")
        self.assertIn("Sleep\tcronman.cron_jobs.sleep.Sleep\n", output)

    @override_cron_settings()
    def test_info_details(self):
        """Test for showing details of given cron job"""
        output = call_command("cron_worker", "info", "Sleep")
        self.assertEqual(
            output,
            "name: Sleep\n"
            "class: cronman.cron_jobs.sleep.Sleep\n"
            "params: seconds=None, path=None, **kwargs\n"
            "description: \n"
            "Test CronJob: sleeps for given number of seconds.\n"
            "No lock - concurrent calls allowed.\n\n",
        )


class RemoteManagerCommandTestCase(BaseCronTestCase):
    """Tests for `cron_remote_manager` command"""

    # ENABLE:

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=True)
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_enable(self, mock_redis):
        """Tests call to cron_remote_manager enable"""
        mock_set = mock_redis.return_value.set
        mock_set.return_value = True
        output = call_command(
            "cron_remote_manager", "enable", "prod-cron01", "prod-cron02"
        )
        self.assertIn(
            "enable prod-cron01 -> True\n" "enable prod-cron02 -> True", output
        )
        mock_set.assert_has_calls(
            [
                mock.call("cron_scheduler:status:prod-cron01", "enabled"),
                mock.call("cron_scheduler:status:prod-cron02", "enabled"),
            ]
        )

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=True)
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_enable_no_redis(self, mock_redis):
        """Tests call to cron_remote_manager enable when Redis is
        unreachable.
        """
        mock_set = mock_redis.return_value.set
        mock_redis.side_effect = redis.ConnectionError
        output = call_command(
            "cron_remote_manager", "enable", "prod-cron01", "prod-cron02"
        )
        self.assertIn(
            "enable prod-cron01 -> None\n" "enable prod-cron02 -> None", output
        )
        mock_set.assert_not_called()

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=False)
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_enable_disabled_in_settings(self, mock_redis):
        """Tests call to cron_remote_manager enable when
        CronRemoteManager is disabled in settings.
        """
        mock_set = mock_redis.return_value.set
        output = call_command(
            "cron_remote_manager", "enable", "prod-cron01", "prod-cron02"
        )
        self.assertIn(
            "enable prod-cron01 -> None\n" "enable prod-cron02 -> None", output
        )
        mock_set.assert_not_called()

    # DISABLE

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=True)
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_disable(self, mock_redis):
        """Tests call to cron_remote_manager disable"""
        mock_set = mock_redis.return_value.set
        mock_set.return_value = True
        output = call_command(
            "cron_remote_manager", "disable", "prod-cron01", "prod-cron02"
        )
        self.assertIn(
            "disable prod-cron01 -> True\n" "disable prod-cron02 -> True",
            output,
        )
        mock_set.assert_has_calls(
            [
                mock.call("cron_scheduler:status:prod-cron01", "disabled"),
                mock.call("cron_scheduler:status:prod-cron02", "disabled"),
            ]
        )

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=True)
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    @mock.patch("cronman.management.commands.cron_remote_manager.time.sleep")
    def test_disable_wait(self, mock_sleep, mock_redis):
        """Tests call to cron_remote_manager disable with wait option"""
        mock_set = mock_redis.return_value.set
        mock_set.return_value = True
        output = call_command(
            "cron_remote_manager",
            "disable",
            "prod-cron01",
            "prod-cron02",
            wait=True,
        )
        self.assertIn(
            "disable prod-cron01 -> True\n" "disable prod-cron02 -> True",
            output,
        )
        mock_set.assert_has_calls(
            [
                mock.call("cron_scheduler:status:prod-cron01", "disabled"),
                mock.call("cron_scheduler:status:prod-cron02", "disabled"),
            ]
        )
        mock_sleep.assert_called_once_with(120)

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=True)
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_disable_no_redis(self, mock_redis):
        """Tests call to cron_remote_manager disable when Redis is
        unreachable.
        """
        mock_set = mock_redis.return_value.set
        mock_redis.side_effect = redis.ConnectionError
        output = call_command(
            "cron_remote_manager", "disable", "prod-cron01", "prod-cron02"
        )
        self.assertIn(
            "disable prod-cron01 -> None\n" "disable prod-cron02 -> None",
            output,
        )
        mock_set.assert_not_called()

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=False)
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_disable_disabled_in_settings(self, mock_redis):
        """Tests call to cron_remote_manager disable when
        CronRemoteManager is disabled in settings.
        """
        mock_set = mock_redis.return_value.set
        output = call_command(
            "cron_remote_manager", "disable", "prod-cron01", "prod-cron02"
        )
        self.assertIn(
            "disable prod-cron01 -> None\n" "disable prod-cron02 -> None",
            output,
        )
        mock_set.assert_not_called()

    # CLEAR_STATUS:

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=True)
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_clear_status(self, mock_redis):
        """Tests call to cron_remote_manager clear_status"""
        mock_delete = mock_redis.return_value.delete
        mock_delete.return_value = 1
        output = call_command(
            "cron_remote_manager", "clear_status", "prod-cron01", "prod-cron02"
        )
        self.assertIn(
            "clear_status prod-cron01 -> 1\n" "clear_status prod-cron02 -> 1",
            output,
        )
        mock_delete.assert_has_calls(
            [
                mock.call("cron_scheduler:status:prod-cron01"),
                mock.call("cron_scheduler:status:prod-cron02"),
            ]
        )

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=True)
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_clear_status_no_redis(self, mock_redis):
        """Tests call to cron_remote_manager clear_status when Redis is
        unreachable.
        """
        mock_delete = mock_redis.return_value.delete
        mock_redis.side_effect = redis.ConnectionError
        output = call_command(
            "cron_remote_manager", "clear_status", "prod-cron01", "prod-cron02"
        )
        self.assertIn(
            "clear_status prod-cron01 -> None\n"
            "clear_status prod-cron02 -> None",
            output,
        )
        mock_delete.assert_not_called()

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=False)
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_clear_status_disabled_in_settings(self, mock_redis):
        """Tests call to cron_remote_manager clear_status when
        CronRemoteManager is disabled in settings.
        """
        mock_delete = mock_redis.return_value.delete
        output = call_command(
            "cron_remote_manager", "clear_status", "prod-cron01", "prod-cron02"
        )
        self.assertIn(
            "clear_status prod-cron01 -> None\n"
            "clear_status prod-cron02 -> None",
            output,
        )
        mock_delete.assert_not_called()

    # CLEAR_STATUS:

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=True)
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_get_status(self, mock_redis):
        """Tests call to cron_remote_manager get_status"""
        mock_get = mock_redis.return_value.get
        mock_get.return_value = "disabled"
        output = call_command(
            "cron_remote_manager", "get_status", "prod-cron01", "prod-cron02"
        )
        self.assertIn(
            "get_status prod-cron01 -> disabled\n"
            "get_status prod-cron02 -> disabled",
            output,
        )
        mock_get.assert_has_calls(
            [
                mock.call("cron_scheduler:status:prod-cron01"),
                mock.call("cron_scheduler:status:prod-cron02"),
            ]
        )

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=True)
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_get_status_no_redis(self, mock_redis):
        """Tests call to cron_remote_manager get_status when Redis is
        unreachable.
        """
        mock_get = mock_redis.return_value.get
        mock_redis.side_effect = redis.ConnectionError
        output = call_command(
            "cron_remote_manager", "get_status", "prod-cron01", "prod-cron02"
        )
        self.assertIn(
            "get_status prod-cron01 -> None\n"
            "get_status prod-cron02 -> None",
            output,
        )
        mock_get.assert_not_called()

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=False)
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_get_status_disabled_in_settings(self, mock_redis):
        """Tests call to cron_remote_manager get_status when
        CronRemoteManager is disabled in settings.
        """
        mock_get = mock_redis.return_value.get
        output = call_command(
            "cron_remote_manager", "get_status", "prod-cron01", "prod-cron02"
        )
        self.assertIn(
            "get_status prod-cron01 -> None\n"
            "get_status prod-cron02 -> None",
            output,
        )
        mock_get.assert_not_called()

    # KILL:

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=True)
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_kill(self, mock_redis):
        """Tests call to cron_remote_manager kill"""
        mock_rpush = mock_redis.return_value.rpush
        mock_rpush.return_value = 1
        output = call_command(
            "cron_remote_manager", "kill:ParseInvoiceData", "prod-cron01"
        )
        self.assertIn("kill:ParseInvoiceData prod-cron01 -> 1", output)
        mock_rpush.assert_has_calls(
            [mock.call("cron_scheduler:kill:prod-cron01", "ParseInvoiceData")]
        )

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=True)
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_kill_no_redis(self, mock_redis):
        """Tests call to cron_remote_manager kill when Redis is
        unreachable.
        """
        mock_rpush = mock_redis.return_value.rpush
        mock_redis.side_effect = redis.ConnectionError
        output = call_command(
            "cron_remote_manager", "kill:ParseInvoiceData", "prod-cron01"
        )
        self.assertIn("kill:ParseInvoiceData prod-cron01 -> None", output)
        mock_rpush.assert_not_called()

    @override_cron_settings(CRONMAN_REMOTE_MANAGER_ENABLED=False)
    @mock.patch(
        "cronman.remote_manager.CronRemoteManager.redis_client",
        new_callable=mock.PropertyMock,
    )
    def test_kill_disabled_in_settings(self, mock_redis):
        """Tests call to cron_remote_manager kill when
        CronRemoteManager is disabled in settings.
        """
        mock_rpush = mock_redis.return_value.rpush
        output = call_command(
            "cron_remote_manager", "kill:ParseInvoiceData", "prod-cron01"
        )
        self.assertIn("kill:ParseInvoiceData prod-cron01 -> None", output)
        mock_rpush.assert_not_called()

    # other cases:

    @override_cron_settings()
    def test_invalid_command_call_no_method(self):
        """Test for invalid scheduler command call: no method"""
        with self.assertRaises(CommandError):
            call_command("cron_remote_manager", "foo")
