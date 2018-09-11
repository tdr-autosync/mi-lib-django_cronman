# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import datetime

from django.utils import timezone

import mock

from cronman.models import CronTask
from cronman.taxonomies import CronTaskStatus
from cronman.tests.base import (
    BaseCronTestCase,
    create_pid_file,
    override_cron_settings,
    patch_kill,
    patch_ps,
)
from cronman.tests.tools import call_worker


class RunCronTasksTestCase(BaseCronTestCase):
    """Tests for RunCronTasks cron job"""

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.run_cron_tasks.connections.close_all")
    @mock.patch("cronman.cron_jobs.run_cron_tasks.CronSpawner.start_worker")
    @mock.patch("cronman.job.logging.getLogger")
    def test_run_no_workers(self, mock_get_logger, mock_start, mock_close_all):
        """Test for RunCronTasks - no CronTask objects started"""
        self.assertTrue(call_worker("RunCronTasks").ok)
        mock_get_logger.return_value.info.assert_has_calls(
            [mock.call("No CronTasks started.")]
        )
        mock_start.assert_not_called()
        mock_close_all.assert_called_once()

    @override_cron_settings()
    @mock.patch("cronman.cron_jobs.run_cron_tasks.connections.close_all")
    @mock.patch("cronman.cron_jobs.run_cron_tasks.CronSpawner.start_worker")
    @mock.patch("cronman.job.logging.getLogger")
    def test_run_3_workers(self, mock_get_logger, mock_start, mock_close_all):
        """Test for RunCronTasks - 3 CronTask objects started"""
        now = timezone.now()
        # Pending Tasks:
        cron_task_c1 = CronTask.objects.run_now(
            "Sleep", now=now - datetime.timedelta(minutes=6)
        )[0]
        cron_task_c2 = CronTask.objects.run_now(
            "ParamsLockedSleep", now=now - datetime.timedelta(minutes=1)
        )[0]
        cron_task_c3 = CronTask.objects.run_now(
            "ClassLockedSleep", now=now - datetime.timedelta(minutes=1)
        )[0]
        cron_task_c3.mark_as_queued()
        # Future Task:
        CronTask.objects.run_now(
            "ClassLockedSleep",
            params="42",
            now=now + datetime.timedelta(minutes=6),
        )
        # Finished Task:
        CronTask.objects.run_now("IgnoreLockErrorsSleep")[0].mark_as_finished()

        self.assertTrue(call_worker("RunCronTasks").ok)

        mock_get_logger.return_value.info.assert_has_calls(
            [mock.call("Started 3 CronTask(s).")]
        )
        mock_start.assert_has_calls(
            [
                mock.call("Sleep:task_id={}".format(cron_task_c1.pk)),
                mock.call(
                    "ParamsLockedSleep:task_id={}".format(cron_task_c2.pk)
                ),
                mock.call(
                    "ClassLockedSleep:task_id={}".format(cron_task_c3.pk)
                ),
            ]
        )
        mock_close_all.assert_called_once()


class CleanCronTasksTestCase(BaseCronTestCase):
    """Tests for CleanCronTasks cron job"""

    @override_cron_settings()
    @mock.patch("cronman.job.logging.getLogger")
    def test_run_no_workers(self, mock_get_logger):
        """Test for CleanCronTasks - no CronTask object marked as failed."""
        self.assertTrue(call_worker("CleanCronTasks").ok)
        mock_get_logger.return_value.info.assert_has_calls(
            [mock.call("No CronTasks marked as failed.")]
        )

    @override_cron_settings()
    @mock.patch("cronman.job.logging.getLogger")
    def test_run_2_started_1_dead(self, mock_get_logger):
        """Test for CleanCronTasks - 2 CronTask objects started, 1 marked as
        failed.
        """
        now = timezone.now()

        # Started Task - running:
        pid_s1 = 1001
        cron_task_s1 = CronTask.objects.run_now(
            "Sleep", now=now - datetime.timedelta(minutes=6)
        )[0]
        cron_task_s1.mark_as_started(pid_s1)

        # Started Task - dead:
        cron_task_s2 = CronTask.objects.run_now(
            "ParamsLockedSleep", now=now - datetime.timedelta(minutes=1)
        )[0]
        pid_s2 = 1002
        cron_task_s2.mark_as_started(pid_s2)

        # Queued Task:
        cron_task_q1 = CronTask.objects.run_now(
            "ClassLockedSleep", now=now - datetime.timedelta(minutes=1)
        )[0]
        cron_task_q1.mark_as_queued()

        # Waiting Task:
        cron_task_w1 = CronTask.objects.run_now(
            "ClassLockedSleep",
            params="42",
            now=now + datetime.timedelta(minutes=6),
        )[0]

        # Finished Task:
        cron_task_f1 = CronTask.objects.run_now("IgnoreLockErrorsSleep")[0]
        cron_task_f1.mark_as_finished()

        create_pid_file(cron_task_s1.job_spec(), pid_s1)
        with patch_ps(active_pids=[pid_s1]):
            with patch_kill(active_pids=[pid_s1]):
                self.assertTrue(call_worker("CleanCronTasks").ok)

        mock_get_logger.return_value.info.assert_has_calls(
            [mock.call("1 CronTask(s) marked as failed.")]
        )

        # Started Task - running - no status change:
        cron_task_s1.refresh_from_db()
        self.assertEqual(cron_task_s1.status, CronTaskStatus.STARTED)

        # Started Task - dead - marked as failed:
        cron_task_s2.refresh_from_db()
        self.assertEqual(cron_task_s2.status, CronTaskStatus.FAILED)

        # Other statuses - no status change:
        cron_task_q1.refresh_from_db()
        self.assertEqual(cron_task_q1.status, CronTaskStatus.QUEUED)
        cron_task_w1.refresh_from_db()
        self.assertEqual(cron_task_w1.status, CronTaskStatus.WAITING)
        cron_task_f1.refresh_from_db()
        self.assertEqual(cron_task_f1.status, CronTaskStatus.FINISHED)
