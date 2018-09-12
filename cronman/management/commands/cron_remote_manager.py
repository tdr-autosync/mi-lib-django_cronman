# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import time

from django.core.management import BaseCommand, CommandError

from cronman.remote_manager import CronRemoteManager
from cronman.scheduler import CronScheduler


class Command(BaseCommand):
    help = (
        "Cron Manager: CLI to control remote Cron Schedulers via Redis.\n"
        "Redis access configuration have to be the same on local and remote "
        "machines.\n"
        "With default configuration, the following settings have to match:\n"
        "CRONMAN_REDIS_HOST, CRONMAN_REDIS_PORT, CRONMAN_REDIS_DB.\n"
    )

    ALLOWED_METHODS = (
        "disable",
        "enable",
        "get_status",
        "clear_status",
        "kill",
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "method",
            help=(
                "Choices: disable, enable, get_status, clear_status, "
                "kill:<jobspec>."
            ),
        )
        parser.add_argument("hosts", nargs="+")
        parser.add_argument(
            "--wait",
            action="store_true",
            default=False,
            help="Wait for Cron Schedulers to receive the request",
        )

    def handle(self, **options):
        """Main command logic"""
        method_string = options["method"]
        if ":" in method_string:
            method_name, arg = method_string.split(":", 1)
            args = (arg,)
        else:
            method_name = method_string
            args = ()
        if method_name not in self.ALLOWED_METHODS:
            raise CommandError(
                'Command "{}" is not allowed'.format(method_name)
            )
        host_names = options["hosts"]
        remote_manager = CronRemoteManager()
        method = getattr(remote_manager, method_name)
        results = []
        for host_name in host_names:
            result = method(*args, host_name=host_name)
            results.append(
                "{} {} -> {}".format(method_string, host_name, result)
            )
        summary = "\n".join(results)
        if options["wait"]:
            time.sleep(CronScheduler.interval * 60)
        return summary
