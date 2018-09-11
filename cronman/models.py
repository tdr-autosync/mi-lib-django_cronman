# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import datetime

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from django.utils.six import python_2_unicode_compatible

from cronman.taxonomies import CronTaskStatus


class CronTaskQuerySet(models.QuerySet):
    """QuerySet for CronTask model"""

    def pending(self):
        """CronTasks with status suitable for start - WAITING or QUEUED"""
        return self.filter(
            status__in=(CronTaskStatus.WAITING, CronTaskStatus.QUEUED)
        )

    def started(self):
        """CronTasks with status STARTED (running)"""
        return self.filter(status=CronTaskStatus.STARTED)

    def failed(self):
        """CronTasks with status FAILED"""
        return self.filter(status=CronTaskStatus.FAILED)

    def finished(self):
        """CronTasks with status FINISHED (success)"""
        return self.filter(status=CronTaskStatus.FINISHED)


# pylint: disable=no-member
class CronTaskManager(models.Manager.from_queryset(CronTaskQuerySet)):
    """Manager for CronTask model"""

    def run_now(self, cron_job, params="", user=None, now=None):
        """Requests a cron job to run now by creating a CronTask instance.
        Prevents duplicated objects from being created.
        """
        now = now or timezone.now()
        tolerance = datetime.timedelta(minutes=4)
        cron_task = self.filter(
            cron_job=cron_job,
            params=params,
            start_at__gt=now - tolerance,
            start_at__lt=now + tolerance,
        ).first()
        if cron_task:
            created = False
        else:
            cron_task = self.create(
                cron_job=cron_job, params=params, user=user, start_at=now
            )
            created = True
        return cron_task, created


@python_2_unicode_compatible
class CronTask(models.Model):
    """Cron Task: a cron job execution request"""

    TASK_ID_PARAM = "task_id"

    cron_job = models.CharField(max_length=255)
    params = models.TextField(blank=True)
    start_at = models.DateTimeField(blank=True, default=timezone.now)

    status = models.CharField(
        max_length=16,
        choices=CronTaskStatus.CHOICES,
        default=CronTaskStatus.WAITING,
    )
    pid = models.PositiveIntegerField(null=True, blank=True)

    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(null=True, auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    objects = CronTaskManager()

    def job_spec(self):
        """Cron Job spec for this task"""
        cron_job = self.cron_job
        params = self.params.strip()
        params += "{}{}={}".format(
            "," if params else "", self.TASK_ID_PARAM, self.pk
        )
        return "{}:{}".format(cron_job, params)

    def __str__(self):
        return self.job_spec()

    # Status check methods:

    def is_pending(self):
        """Check if this CronTask is suitable to launch - WAITING or QUEUED"""
        return self.status in (CronTaskStatus.WAITING, CronTaskStatus.QUEUED)

    def is_started(self):
        """Check if this CronTask has status STARTED (running)"""
        return self.status == CronTaskStatus.STARTED

    def is_failed(self):
        """Check if this CronTask has status FAILED"""
        return self.status == CronTaskStatus.FAILED

    def is_finished(self):
        """Check if this CronTask has status FINISHED (success)"""
        return self.status == CronTaskStatus.FINISHED

    # Status change methods:

    def mark_as_queued(self):
        """Marks this CronTask as QUEUED"""
        self.status = CronTaskStatus.QUEUED
        self.save()

    def mark_as_started(self, pid, date_time=None):
        """Marks this CronTask as QUEUED - retrieved by worker process."""
        self.status = CronTaskStatus.STARTED
        self.pid = pid
        self.started_at = date_time or timezone.now()
        self.save()

    def mark_as_failed(self):
        """Marks this CronTask as FAILED"""
        self.status = CronTaskStatus.FAILED
        self.save()

    def mark_as_finished(self, date_time=None):
        """Marks this CronTask as FINISHED successfully"""
        self.status = CronTaskStatus.FINISHED
        self.finished_at = date_time or timezone.now()
        self.save()
