# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

from django.test import override_settings
from django.utils import timezone

from cronman.forms import CronTaskAdminForm
from cronman.models import CronTask
from cronman.tests import cron_jobs
from cronman.tests.base import BaseCronTestCase


class CronTaskAdminFormTestCase(BaseCronTestCase):
    """Tests for CronTaskAdminForm"""

    @override_settings(CRONMAN_JOBS_MODULE=None)
    def test_cron_job_choices_empty(self):
        """Test that cron job choices are empty when CRONMAN_JOBS_MODULE is not
        set.
        """
        form = CronTaskAdminForm(instance=CronTask())
        self.assertEqual(form.fields["cron_job"].choices, [])

    @override_settings(CRONMAN_JOBS_MODULE="cronman.tests.cron_jobs")
    def test_cron_job_choices_matching(self):
        """Test that cron job choices are matching CRONMAN_JOBS_MODULE
        configuration.
        """
        form = CronTaskAdminForm(instance=CronTask())
        self.assertEqual(
            set(
                value
                for value, verbose_name in form.fields["cron_job"].choices
            ),
            set(cron_jobs.ALLOWED_CRON_TASKS),
        )

    @override_settings(CRONMAN_JOBS_MODULE="cronman.tests.cron_jobs")
    def test_valid_form_no_params(self):
        """Test for valid form - no cron job params"""
        now = timezone.now()
        cron_job = "Sleep"
        form = CronTaskAdminForm(
            data={"cron_job": cron_job, "start_at": now}, instance=CronTask()
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data,
            {"cron_job": cron_job, "params": "", "start_at": now},
        )

    @override_settings(CRONMAN_JOBS_MODULE="cronman.tests.cron_jobs")
    def test_valid_form_with_params(self):
        """Test for valid form - valid cron job params"""
        now = timezone.now()
        cron_job = "Sleep"
        params = 'makers="Toyota;Audi"'
        form = CronTaskAdminForm(
            data={"cron_job": cron_job, "params": params, "start_at": now},
            instance=CronTask(),
        )
        self.assertTrue(form.is_valid())
        self.assertEqual(
            form.cleaned_data,
            {"cron_job": cron_job, "params": params, "start_at": now},
        )

    @override_settings(CRONMAN_JOBS_MODULE="cronman.tests.cron_jobs")
    def test_invalid_params(self):
        """Test for invalid form - invalid cron job params"""
        now = timezone.now()
        cron_job = "Sleep"
        params = 'makers="Toyota;Audi",1234'  # params syntax error
        form = CronTaskAdminForm(
            data={"cron_job": cron_job, "params": params, "start_at": now},
            instance=CronTask(),
        )
        self.assertFalse(form.is_valid())
