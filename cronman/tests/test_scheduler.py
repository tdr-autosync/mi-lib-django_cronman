# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import datetime

import mock

from cronman.scheduler import CronScheduler
from cronman.tests.base import (
    TEMP_FILE,
    BaseCronTestCase,
    override_cron_settings,
)


class CronSchedulerTestCase(BaseCronTestCase):
    """Tests for CronScheduler class"""

    # Main methods

    @override_cron_settings(CRONMAN_JOBS_MODULE=None)
    @mock.patch("cronman.scheduler.scheduler.CronSpawner.start_worker")
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    def test_run_no_workers(self, mock_cron_worker, mock_start):
        """Test for CronScheduler.run method - no workers started"""
        scheduler = CronScheduler()
        output = scheduler.run()
        self.assertIn("No jobs started.\n", output)
        mock_start.assert_not_called()
        mock_cron_worker.return_value.resume.assert_not_called()

    @override_cron_settings()
    @mock.patch("cronman.scheduler.scheduler.CronSpawner.start_worker")
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    def test_run_2_workers(self, mock_cron_worker, mock_start):
        """Test for CronScheduler.run method - 2 workers started"""
        scheduler = CronScheduler()
        output = scheduler.run()
        self.assertIn("Started 2 job(s)", output)
        mock_start.assert_has_calls(
            [
                mock.call("Sleep:seconds=1,path={}".format(TEMP_FILE)),
                mock.call("Sleep:seconds=2"),
            ]
        )
        mock_cron_worker.return_value.resume.assert_not_called()

    @override_cron_settings()
    @mock.patch("cronman.scheduler.scheduler.CronSpawner.start_worker")
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    def test_run_resume(self, mock_cron_worker, mock_start):
        """Test for CronScheduler.run method with resume file"""
        scheduler = CronScheduler()
        scheduler.resume_file.create()
        scheduler.run()
        mock_cron_worker.return_value.resume.assert_called_once()
        self.assertFalse(scheduler.resume_file.exists())  # resume file deleted

    @override_cron_settings()
    @mock.patch("cronman.scheduler.scheduler.CronSpawner.start_worker")
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    def test_run_disabled(self, mock_cron_worker, mock_start):
        """Test for CronScheduler.run method when lock is acquired"""
        scheduler = CronScheduler()
        scheduler.lock_file.create()
        output = scheduler.run()
        self.assertIn(
            "CronSchedulerLocked: "
            "Scheduler is disabled (lock file exists). "
            'To enable it again, please run "cron_scheduler enable". '
            "Quitting now.\n",
            output,
        )
        mock_start.assert_not_called()
        mock_cron_worker.return_value.resume.assert_not_called()

    @override_cron_settings()
    @mock.patch(
        "cronman.scheduler.scheduler.CronSpawner.start_worker",
        return_value=None,
    )
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    def test_run_cannot_spawn_process(self, mock_cron_worker, mock_start):
        """Test for CronScheduler.run method - case: cannot spawn process"""
        scheduler = CronScheduler()
        scheduler.slack = mock.MagicMock()
        scheduler.logger = mock.MagicMock()
        output = scheduler.run()
        mock_start.assert_has_calls(
            [
                mock.call("Sleep:seconds=1,path={}".format(TEMP_FILE)),
                mock.call("Sleep:seconds=2"),
            ]
        )
        self.assertIn("No jobs started.", output)
        mock_cron_worker.return_value.resume.assert_not_called()

    @override_cron_settings()
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    def test_disable(self, mock_cron_worker):
        """Test for CronScheduler.disable method - OK"""
        scheduler = CronScheduler()
        output = scheduler.disable()
        self.assertIn("Scheduler disabled (lock file created).\n", output)
        self.assertTrue(scheduler.lock_file.exists())
        mock_cron_worker.return_value.suspend.assert_not_called()

    @override_cron_settings()
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    def test_disable_with_workers(self, mock_cron_worker):
        """Test for CronScheduler.disable method with workers option - OK"""
        scheduler = CronScheduler()
        output = scheduler.disable(workers=True)
        self.assertIn(
            "Scheduler disabled (lock file created, workers suspended).\n",
            output,
        )
        self.assertTrue(scheduler.lock_file.exists())
        mock_cron_worker.return_value.suspend.assert_called_once()

    @override_cron_settings()
    @mock.patch(
        "cronman.scheduler.scheduler.CronScheduler.cron_worker",
        new_callable=mock.PropertyMock,
    )
    def test_disable_already_disabled(self, mock_cron_worker):
        """Test for CronScheduler.disable method - FAIL, already disabled"""
        scheduler = CronScheduler()
        scheduler.lock_file.create()
        output = scheduler.disable()
        self.assertIn(
            "CronSchedulerLocked: "
            "Scheduler is already disabled (lock file exists).",
            output,
        )
        self.assertTrue(scheduler.lock_file.exists())
        mock_cron_worker.return_value.suspend.assert_not_called()

    @override_cron_settings()
    def test_enable(self):
        """Test for CronScheduler.enable method - OK"""
        scheduler = CronScheduler()
        scheduler.lock_file.create()
        output = scheduler.enable()
        self.assertIn("Scheduler enabled (lock file deleted).\n", output)
        self.assertFalse(scheduler.lock_file.exists())
        self.assertFalse(scheduler.resume_file.exists())

    @override_cron_settings()
    def test_enable_with_workers(self):
        """Test for CronScheduler.enable method with workers option - OK"""
        scheduler = CronScheduler()
        scheduler.lock_file.create()
        output = scheduler.enable(workers=True)
        self.assertIn(
            "Scheduler enabled (resume file created, lock file deleted).\n",
            output,
        )
        self.assertFalse(scheduler.lock_file.exists())
        self.assertTrue(scheduler.resume_file.exists())

    @override_cron_settings()
    def test_enable_already_enabled(self):
        """Test for CronScheduler.enable method - FAIL, already enabled"""
        scheduler = CronScheduler()
        output = scheduler.enable()
        self.assertIn(
            "CronSchedulerUnlocked: "
            "Scheduler is already enabled (lock file does not exist).",
            output,
        )
        self.assertFalse(scheduler.lock_file.exists())
        self.assertFalse(scheduler.resume_file.exists())

    # Helpers

    @override_cron_settings()
    def test_get_datetime_range(self):
        """Test for CronScheduler.get_datetime_range method"""
        now = datetime.datetime(2017, 5, 13, 12, 1, 3, 321)
        self.assertEqual(
            CronScheduler(now=now).get_datetime_range(),
            (
                datetime.datetime(2017, 5, 13, 12, 0, 59),
                datetime.datetime(2017, 5, 13, 12, 2, 59),
            ),
        )

    @override_cron_settings()
    def test_cron_jobs(self):
        """Test that cron_jobs property is correct (CRON_JOBS property of
        settings.CRONMAN_JOBS_MODULE).
        """
        scheduler = CronScheduler()
        from cronman.tests.cron_jobs import CRON_JOBS

        self.assertEqual(scheduler.cron_jobs, CRON_JOBS)

    @override_cron_settings(CRONMAN_JOBS_MODULE=None)
    def test_cron_jobs_empty(self):
        """Test that cron_jobs property is empty tuple when CRONMAN_JOBS_MODULE
        is not set.
        """
        scheduler = CronScheduler()
        self.assertEqual(scheduler.cron_jobs, ())

    @override_cron_settings(CRONMAN_JOBS_MODULE="module.does.not.exist")
    def test_cron_jobs_import_error(self):
        """Test that cron_jobs property raises ImportError when
        CRONMAN_JOBS_MODULE is not a valid module."""
        scheduler = CronScheduler()
        with self.assertRaises(ImportError):
            self.assertEqual(scheduler.cron_jobs, ())

    @override_cron_settings()
    def test_get_jobs(self):
        """Test for CronScheduler.get_jobs method"""
        now = datetime.datetime(2017, 5, 13, 12, 1, 3, 321)
        self.assertEqual(
            CronScheduler(now=now).get_jobs(),
            [
                ("*/2 * * * *", "Sleep:seconds=1,path={}".format(TEMP_FILE)),
                ("*/2 * * * *", "Sleep:seconds=2"),
            ],
        )
