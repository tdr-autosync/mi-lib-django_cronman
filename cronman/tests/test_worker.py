# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import platform

import mock

from cronman.exceptions import CronWorkerInvalidParams
from cronman.models import CronTask
from cronman.taxonomies import CronTaskStatus
from cronman.tests.base import (
    BaseCronTestCase,
    create_pid_file,
    override_cron_settings,
    patch_kill,
    patch_ps,
)
from cronman.worker import CronWorker

SYSTEM_NAME = platform.node()


class CronWorkerTestCase(BaseCronTestCase):
    """Tests for CronWorker class"""

    # Main methods

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.Sleep.run")
    def test_run_without_params(self, mock_run):
        """Test for CronWorker.run method - run cron job without params"""
        worker = CronWorker()
        output = worker.run("Sleep")
        self.assertIn("OK: Processed Sleep", output)
        mock_run.assert_called_once_with()

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.Sleep.run")
    def test_run_with_params(self, mock_run):
        """Test for CronWorker.run method - run cron job with params"""
        worker = CronWorker()
        output = worker.run("Sleep:42,path=/tmp/test")
        self.assertIn("OK: Processed Sleep:42,path=/tmp/test", output)
        mock_run.assert_called_once_with("42", path="/tmp/test")

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.Sleep.run")
    def test_run_non_existing_cron_job(self, mock_run):
        """Test for CronWorker.run method - attempt to run non existing
        cron job
        """
        worker = CronWorker()
        with self.assertRaisesMessage(
            CronWorkerInvalidParams,
            "CronJobNotRegistered: {!r}".format("NoSuchWorker"),
        ):
            worker.run("NoSuchWorker")
        mock_run.assert_not_called()

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.Sleep.run")
    def test_run_invalid_params(self, mock_run):
        """Test for CronWorker.run method - attempt to run cron job with
        invalid params
        """
        worker = CronWorker()
        with self.assertRaisesMessage(
            CronWorkerInvalidParams,
            "ValueError: In chars 9-10 `5`: "
            "Positional argument after named arguments.",
        ):
            worker.run("Sleep:2,test=3,5")  # positional arg. after named one
        mock_run.assert_not_called()

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.Sleep.run", side_effect=ValueError)
    def test_run_cron_job_error(self, mock_run):
        """Test for CronWorker.run method - exception raised while processing
        """
        worker = CronWorker()
        output = worker.run("Sleep")
        self.assertIn("FAIL: Processed Sleep", output)
        mock_run.assert_called_once_with()

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.ClassLockedSleep.run")
    def test_run_cron_job_while_class_lock_enabled(self, mock_run):
        """Test for CronWorker.run method -
        attempt to run while class-based lock enabled.
        """
        worker = CronWorker()
        worker.slack = mock.MagicMock()
        create_pid_file("ClassLockedSleep")
        output = worker.run("ClassLockedSleep")
        self.assertIn(
            "CronWorkerLocked: "
            'Unable to start "ClassLockedSleep", '
            "because similar process is already running (PID file exists).",
            output,
        )
        mock_run.assert_not_called()
        worker.slack.post.assert_called_once_with(
            (
                "[{}] "
                "CronWorkerLocked: "
                'Unable to start "ClassLockedSleep", '
                "because similar process is already running (PID file exists)."
            ).format(SYSTEM_NAME)
        )

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.ParamsLockedSleep.run")
    def test_run_cron_job_while_params_lock_enabled(self, mock_run):
        """Test for CronWorker.run method -
        attempt to run while params-based lock enabled.
        """
        worker = CronWorker()
        worker.slack = mock.MagicMock()
        create_pid_file("ParamsLockedSleep")
        output = worker.run("ParamsLockedSleep")
        self.assertIn(
            "CronWorkerLocked: "
            'Unable to start "ParamsLockedSleep", '
            "because similar process is already running (PID file exists).",
            output,
        )
        mock_run.assert_not_called()
        worker.slack.post.assert_called_once_with(
            (
                "[{}] "
                "CronWorkerLocked: "
                'Unable to start "ParamsLockedSleep", '
                "because similar process is already running (PID file exists)."
            ).format(SYSTEM_NAME)
        )

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.IgnoreLockErrorsSleep.run")
    def test_run_cron_job_with_lock_ignore_errors(self, mock_run):
        """Test for CronWorker.run method -
        attempt to run while params-based lock enabled and `lock_ignore_errors`
        option is set.
        """
        worker = CronWorker()
        worker.slack = mock.MagicMock()
        create_pid_file("IgnoreLockErrorsSleep")
        output = worker.run("IgnoreLockErrorsSleep")
        self.assertIn(
            "CronWorkerLocked: "
            'Unable to start "IgnoreLockErrorsSleep", '
            "because similar process is already running (PID file exists).",
            output,
        )
        mock_run.assert_not_called()
        worker.slack.post.assert_not_called()

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.SlackNotifyDoneSleep.run")
    def test_run_cron_job_with_slack_notify_done(self, mock_run):
        """Test for CronWorker.run method - run cron job with
        `slack_notify_done` option set.
        """
        worker = CronWorker()
        worker.slack = mock.MagicMock()
        output = worker.run("SlackNotifyDoneSleep")
        self.assertIn("OK: Processed SlackNotifyDoneSleep", output)
        mock_run.assert_called_once_with()
        worker.slack.post.assert_called_once_with(
            'Cron job "SlackNotifyDoneSleep" is done.'
        )

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.Sleep.run")
    def test_run_cron_job_without_slack_notify_done(self, mock_run):
        """Test for CronWorker.run method - run cron job without
        `slack_notify_done` option set.
        """
        worker = CronWorker()
        worker.slack = mock.MagicMock()
        output = worker.run("Sleep")
        self.assertIn("OK: Processed Sleep", output)
        worker.slack.post.assert_not_called()

    # Tests for Cron Worker + Cron Tasks:

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.Sleep.run")
    def test_run_missing_task(self, mock_run):
        """Test for CronWorker.run method - run DELETED CronTask"""
        cron_task = CronTask.objects.run_now("Sleep")[0]
        job_spec = cron_task.job_spec()
        cron_task.delete()
        worker = CronWorker()
        output = worker.run(job_spec)

        mock_run.assert_called_once_with()
        self.assertIn("OK:", output)  # Cron job passes anyway

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.Sleep.run")
    def test_run_task_without_params(self, mock_run):
        """Test for CronWorker.run method - run CronTask without params"""
        cron_task = CronTask.objects.run_now("Sleep")[0]
        worker = CronWorker()
        worker.run(cron_task.job_spec())

        mock_run.assert_called_once_with()
        cron_task.refresh_from_db()
        self.assertEqual(cron_task.status, CronTaskStatus.FINISHED)

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.Sleep.run")
    def test_run_task_with_params(self, mock_run):
        """Test for CronWorker.run method - run CronTask with params"""
        cron_task = CronTask.objects.run_now(
            "Sleep", params="42,path=/tmp/test"
        )[0]
        worker = CronWorker()
        worker.run(cron_task.job_spec())

        mock_run.assert_called_once_with("42", path="/tmp/test")
        cron_task.refresh_from_db()
        self.assertEqual(cron_task.status, CronTaskStatus.FINISHED)

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.Sleep.run", side_effect=ValueError)
    def test_run_task_error(self, mock_run):
        """Test for CronWorker.run method - exception raised while processing
        CronTask.
        """
        cron_task = CronTask.objects.run_now("Sleep")[0]
        worker = CronWorker()
        worker.run(cron_task.job_spec())

        mock_run.assert_called_once_with()
        cron_task.refresh_from_db()
        self.assertEqual(cron_task.status, CronTaskStatus.FAILED)

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.ClassLockedSleep.run")
    def test_run_task_while_class_lock_enabled(self, mock_run):
        """Test for CronWorker.run method -
        attempt to run CronTask while class-based lock enabled.
        """
        cron_task = CronTask.objects.run_now("ClassLockedSleep")[0]
        worker = CronWorker()
        worker.slack = mock.MagicMock()
        create_pid_file(cron_task.cron_job)
        worker.run(cron_task.job_spec())

        mock_run.assert_not_called()
        cron_task.refresh_from_db()
        self.assertEqual(cron_task.status, CronTaskStatus.QUEUED)

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.ClassLockedSleep.run")
    def test_run_task_with_invalid_status(self, mock_run):
        """Test for CronWorker.run method -
        attempt to run CronTask with invalid status.
        """
        cron_task = CronTask.objects.run_now("ClassLockedSleep")[0]
        cron_task.mark_as_failed()

        worker = CronWorker()
        worker.slack = mock.MagicMock()
        worker.logger = mock.MagicMock()
        output = worker.run(cron_task.job_spec())

        message = (
            "CronTaskInvalidStatus: "
            'Unable to start "ClassLockedSleep:task_id={}", '
            "because associated CronTask "
            'has invalid status "Failed".'.format(cron_task.pk)
        )
        self.assertIn(message, output)
        worker.logger.warning.assert_called_once_with(message)
        worker.slack.post.assert_called_once_with(
            "[{}] {}".format(SYSTEM_NAME, message)
        )
        mock_run.assert_not_called()

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.ClassLockedSleep.run")
    def test_run_killed_task(self, mock_run):
        """Test for CronWorker.run method - resuming killed CronTask."""
        pid = 1001
        cron_task = CronTask.objects.run_now("ClassLockedSleep")[0]
        cron_task.mark_as_started(pid)
        with patch_ps():
            with patch_kill():
                worker = CronWorker()
                worker.slack = mock.MagicMock()
                worker.logger = mock.MagicMock()
                output = worker.run(cron_task.job_spec())

        self.assertIn("OK:", output)
        worker.logger.info.assert_has_calls(
            [
                mock.call(
                    'Starting "ClassLockedSleep:task_id={}" '
                    "for killed CronTask.".format(cron_task.pk)
                )
            ]
        )
        mock_run.assert_called_once_with()

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.sleep.ClassLockedSleep.run")
    def test_run_task_already_started(self, mock_run):
        """Test for CronWorker.run method -
        attempt to run already started CronTask.
        """
        pid = 1001
        cron_task = CronTask.objects.run_now("ClassLockedSleep")[0]
        cron_task.mark_as_started(pid)
        with patch_ps(active_pids=[pid]):
            with patch_kill(active_pids=[pid]):
                worker = CronWorker()
                worker.slack = mock.MagicMock()
                worker.logger = mock.MagicMock()
                output = worker.run(cron_task.job_spec())

        message = (
            "CronTaskInvalidStatus: "
            'Unable to start "ClassLockedSleep:task_id={}", '
            "because associated CronTask "
            'has invalid status "Started".'.format(cron_task.pk)
        )
        self.assertIn(message, output)
        worker.logger.warning.assert_called_once_with(message)
        worker.slack.post.assert_called_once_with(
            "[{}] {}".format(SYSTEM_NAME, message)
        )
        mock_run.assert_not_called()
