# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

from django.core.management import BaseCommand, CommandError

from cronman.scheduler import CronScheduler


class Command(BaseCommand):
    help = (
        "Cron Scheduler: determines which CronJobs should be started in "
        "current period and starts each of them in a worker process."
    )

    def add_arguments(self, parser):
        parser.add_argument("method", choices=("run", "disable", "enable"))
        parser.add_argument("--workers", action="store_true")

    def handle(self, **options):
        """Main command logic"""
        method_name = options["method"]
        workers = options["workers"]
        scheduler = CronScheduler()
        method = getattr(scheduler, method_name)
        if method_name == "run":
            if workers:
                raise CommandError(
                    'Subcommand "{}" does not accept --workers option.'.format(
                        method_name
                    )
                )
            return method()
        else:
            return method(workers=workers)
