# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

from django.core.management import BaseCommand, CommandError

from cronman.worker import CronWorker


class Command(BaseCommand):
    help = "Cron Worker: runs a single CronJob"

    def add_arguments(self, parser):
        parser.add_argument(
            "method",
            choices=(
                "run",
                "status",
                "kill",
                "info",
                "clean",
                "suspend",
                "resume",
            ),
        )
        parser.add_argument("arg", nargs="?")

    def handle(self, **options):
        """Main command logic"""
        method_name = options["method"]
        arg = options["arg"]

        worker = CronWorker()
        method = getattr(worker, method_name)

        if not arg:
            if method_name == "run":
                raise CommandError("Job specification is required.")
        if arg:
            if method_name in ("clean", "suspend"):
                raise CommandError(
                    'Subcommand "{}" does not accept arguments.'.format(
                        method_name
                    )
                )
            return method(arg)
        else:
            return method()
