# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import logging
import signal
import sys

from cronman.monitor import Slack

logger = logging.getLogger("cronman.command.cron_worker")


class SignalNotifier(object):
    """Class responsible for sending notifications when SIGINT / SIGTERM
    is received.
    """

    signal_names = ((signal.SIGINT, "SIGINT"), (signal.SIGTERM, "SIGTERM"))

    def __init__(self, job_name):
        self.job_name = job_name
        self.logger = logger
        self.slack = Slack()
        self.previous_int_handler = signal.getsignal(signal.SIGINT)
        self.previous_term_handler = signal.getsignal(signal.SIGTERM)

    def notify_and_quit(self, signum, frame):
        """Handles a signal by sending notification and quitting"""
        message = 'Cron job "{}" killed by {}.'.format(
            self.job_name, dict(self.signal_names).get(signum, signum)
        )
        self.logger.warning(message)
        self.slack.post(message)
        sys.exit(signum)

    def capture(self):
        """Assigns handlers to signals"""
        self.previous_int_handler = signal.signal(
            signal.SIGINT, self.notify_and_quit
        )
        self.previous_term_handler = signal.signal(
            signal.SIGTERM, self.notify_and_quit
        )

    def reset(self):
        """Restores previous signal handlers"""
        signal.signal(signal.SIGINT, self.previous_int_handler)
        signal.signal(signal.SIGTERM, self.previous_term_handler)

    def __enter__(self):
        self.capture()
        return self

    def __exit__(self, *args, **kwargs):
        self.reset()
