# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import logging
import platform

from cronman.monitor import Cronitor, Sentry, Slack
from cronman.utils import bool_param, config, ensure_dir, format_exception

logger = logging.getLogger("cronman.command")


class BaseCronObject(object):
    """Common base class for CronRemoteManager, CronScheduler, CronSpawner,
    CronWorker.
    """

    def __init__(self, **kwargs):
        self.data_dir = kwargs.get("data_dir", config("CRONMAN_DATA_DIR"))
        self.debug = kwargs.get("debug", bool_param(config("CRONMAN_DEBUG")))
        self.cronitor = Cronitor()
        self.sentry = Sentry()
        self.slack = Slack()
        ensure_dir(self.data_dir)
        self.logger = kwargs.get("logger", logger)

    def warning(self, exception, silent=False):
        """Handles exception as warning"""
        message = format_exception(exception)
        if not silent:
            self.logger.warning(message)
            system_name = platform.node()
            self.slack.post(
                "[{host}] {message}".format(host=system_name, message=message)
            )
        return message + "\n"  # to be printed on stdout
