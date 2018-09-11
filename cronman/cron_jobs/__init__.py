# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

from cronman.cron_jobs.clean_cron_tasks import (
    CleanCronTasks,
    MotoCleanCronTasks,
)
from cronman.cron_jobs.run_cron_tasks import MotoRunCronTasks, RunCronTasks
from cronman.cron_jobs.sleep import (
    ClassLockedSleep,
    IdleIOSleep,
    IgnoreLockErrorsSleep,
    LowCPUSleep,
    LowestCPUIOSleep,
    ParamsLockedSleep,
    PersistentSleep,
    PersistentSleep2,
    SlackNotifyDoneSleep,
    Sleep,
)
from cronman.job import cron_job_registry

cron_job_registry.register(RunCronTasks)
cron_job_registry.register(MotoRunCronTasks)
cron_job_registry.register(CleanCronTasks)
cron_job_registry.register(MotoCleanCronTasks)
cron_job_registry.register(Sleep)
cron_job_registry.register(ClassLockedSleep)
cron_job_registry.register(ParamsLockedSleep)
cron_job_registry.register(IgnoreLockErrorsSleep)
cron_job_registry.register(SlackNotifyDoneSleep)
cron_job_registry.register(LowCPUSleep)
cron_job_registry.register(LowestCPUIOSleep)
cron_job_registry.register(IdleIOSleep)
cron_job_registry.register(PersistentSleep)
cron_job_registry.register(PersistentSleep2)
