# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

from django.utils import timezone

from cronman.models import CronTask
from cronman.taxonomies import CronTaskStatus
from cronman.tests.base import BaseCronTestCase


class CronTaskTestCase(BaseCronTestCase):
    """Tests for CronTask model"""

    def test_job_spec_no_params(self):
        """Test for CronTask.job_spec method - no params"""
        cron_task = CronTask.objects.run_now("Sleep")[0]
        self.assertEqual(
            cron_task.job_spec(), "Sleep:task_id={}".format(cron_task.pk)
        )

    def test_job_spec_with_params(self):
        """Test for CronTask.job_spec method - with params"""
        cron_task = CronTask.objects.run_now("Sleep", params="seconds=42")[0]
        self.assertEqual(
            cron_task.job_spec(),
            "Sleep:seconds=42,task_id={}".format(cron_task.pk),
        )

    def test_waiting(self):
        """Test for CronTask model instance with WAITING status"""
        cron_task = CronTask.objects.run_now("Sleep")[0]
        self.assertEqual(cron_task.status, CronTaskStatus.WAITING)

        self.assertTrue(cron_task.is_pending())
        self.assertFalse(cron_task.is_started())
        self.assertFalse(cron_task.is_failed())
        self.assertFalse(cron_task.is_finished())

        self.assertEqual(list(CronTask.objects.pending()), [cron_task])
        self.assertEqual(list(CronTask.objects.started()), [])
        self.assertEqual(list(CronTask.objects.failed()), [])
        self.assertEqual(list(CronTask.objects.finished()), [])

    def test_queued(self):
        """Test for CronTask model instance with QUEUED status"""
        cron_task = CronTask.objects.run_now("Sleep")[0]
        cron_task.mark_as_queued()
        self.assertEqual(cron_task.status, CronTaskStatus.QUEUED)

        self.assertTrue(cron_task.is_pending())
        self.assertFalse(cron_task.is_started())
        self.assertFalse(cron_task.is_failed())
        self.assertFalse(cron_task.is_finished())

        self.assertEqual(list(CronTask.objects.pending()), [cron_task])
        self.assertEqual(list(CronTask.objects.started()), [])
        self.assertEqual(list(CronTask.objects.failed()), [])
        self.assertEqual(list(CronTask.objects.finished()), [])

    def test_started(self):
        """Test for CronTask model instance with STARTED status"""
        pid = 1001
        now = timezone.now()
        cron_task = CronTask.objects.run_now("Sleep")[0]
        cron_task.mark_as_started(pid, date_time=now)
        self.assertEqual(cron_task.status, CronTaskStatus.STARTED)
        self.assertEqual(cron_task.pid, pid)
        self.assertEqual(cron_task.started_at, now)

        self.assertFalse(cron_task.is_pending())
        self.assertTrue(cron_task.is_started())
        self.assertFalse(cron_task.is_failed())
        self.assertFalse(cron_task.is_finished())

        self.assertEqual(list(CronTask.objects.pending()), [])
        self.assertEqual(list(CronTask.objects.started()), [cron_task])
        self.assertEqual(list(CronTask.objects.failed()), [])
        self.assertEqual(list(CronTask.objects.finished()), [])

    def test_failed(self):
        """Test for CronTask model instance with FAILED status"""
        cron_task = CronTask.objects.run_now("Sleep")[0]
        cron_task.mark_as_failed()
        self.assertEqual(cron_task.status, CronTaskStatus.FAILED)

        self.assertFalse(cron_task.is_pending())
        self.assertFalse(cron_task.is_started())
        self.assertTrue(cron_task.is_failed())
        self.assertFalse(cron_task.is_finished())

        self.assertEqual(list(CronTask.objects.pending()), [])
        self.assertEqual(list(CronTask.objects.started()), [])
        self.assertEqual(list(CronTask.objects.failed()), [cron_task])
        self.assertEqual(list(CronTask.objects.finished()), [])

    def test_finished(self):
        """Test for CronTask model instance with FINISHED status"""
        now = timezone.now()
        cron_task = CronTask.objects.run_now("Sleep")[0]
        cron_task.mark_as_finished(date_time=now)
        self.assertEqual(cron_task.status, CronTaskStatus.FINISHED)
        self.assertEqual(cron_task.finished_at, now)

        self.assertFalse(cron_task.is_pending())
        self.assertFalse(cron_task.is_started())
        self.assertFalse(cron_task.is_failed())
        self.assertTrue(cron_task.is_finished())

        self.assertEqual(list(CronTask.objects.pending()), [])
        self.assertEqual(list(CronTask.objects.started()), [])
        self.assertEqual(list(CronTask.objects.failed()), [])
        self.assertEqual(list(CronTask.objects.finished()), [cron_task])
