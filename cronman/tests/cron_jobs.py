# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

from cronman.tests.base import TEMP_FILE

CRON_JOBS = (
    ("*/2 * * * *", "Sleep:seconds=1,path={}".format(TEMP_FILE)),
    ("*/2 * * * *", "Sleep:seconds=2"),
)

ALLOWED_CRON_TASKS = ("Sleep", "ParamsLockedSleep", "ClassLockedSleep")
