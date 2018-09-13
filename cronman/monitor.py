# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import logging

from django.conf import settings
from django.utils.html import strip_tags
from django.utils.http import urlencode
from django.utils.six.moves import html_parser as HTMLParser

import raven
import requests

from cronman.utils import bool_param, chunks, config, format_exception

logger = logging.getLogger("cronman.command")


def get_raven_client():
    """Creates raven.Client instance configured to work with cron jobs."""
    # NOTE: this function uses settings and therefore it shouldn't be called
    #       at module level.
    return raven.Client(**settings.RAVEN_CONFIG)


class Cronitor(object):
    """Wrapper over Cronitor web API"""

    def __init__(self):
        self.logger = logger
        self.enabled = bool_param(config("CRONMAN_CRONITOR_ENABLED"))
        self.url = settings.CRONMAN_CRONITOR_URL

    def run(self, cronitor_id, msg=None):
        """Pings Cronitor when job started"""
        self._ping(cronitor_id, "run", msg)

    def complete(self, cronitor_id, msg=None):
        """Pings Conitor when job is done"""
        self._ping(cronitor_id, "complete", msg)

    def fail(self, cronitor_id, msg=None):
        """Pings Cronitor when job failed"""
        self._ping(cronitor_id, "fail", msg)

    def _ping(self, cronitor_id, end_point, msg):
        """Sends a request to Cronitor web API"""
        if not self.enabled:
            self.logger.warning(
                "Cronitor request ignored (disabled in settings)."
            )
            return
        url = self.url.format(cronitor_id=cronitor_id, end_point=end_point)
        params = {"msg": msg} if msg else None
        try:
            response = requests.head(url, params=params, timeout=10)
            response.raise_for_status()
        except requests.RequestException as error:
            # Catch all network and HTTP errors raised by `requests`
            self.logger.warning(
                "Cronitor request failed: {} {}".format(
                    url, format_exception(error)
                )
            )


class Sentry(object):
    """Wrapper over Sentry API"""

    def __init__(self):
        self.raven_client = get_raven_client()
        self.raven_cmd = settings.CRONMAN_RAVEN_CMD

    @property
    def capture_exceptions(self):
        return self.raven_client.capture_exceptions

    @property
    def capture_exception(self):
        return self.raven_client.captureException


def send_errors_to_sentry(method):
    """Decorator for CronScheduler / CronWorker public methods aimed to send
    unhandled exceptions to Sentry.
    """

    def _method(self, *args, **kwargs):
        with self.sentry.capture_exceptions():
            output = method(self, *args, **kwargs)
        return output

    return _method


class Slack(object):
    """Wrapper over Slack web API"""

    def __init__(self):
        self.logger = logger
        self.enabled = bool_param(config("CRONMAN_SLACK_ENABLED"))
        self.url = settings.CRONMAN_SLACK_URL
        self.token = settings.CRONMAN_SLACK_TOKEN
        self.default_channel = settings.CRONMAN_SLACK_DEFAULT_CHANNEL

    def _prepare_message(self, message):
        # slack don't process html entities
        html_parser = HTMLParser.HTMLParser()
        message = html_parser.unescape(message)
        # slack also don't render html itself
        message = strip_tags(message)
        return message

    def post(self, message, channel=None):
        """Posts a message to Slack channel"""
        if not self.enabled:
            self.logger.warning(
                "Slack request ignored (disabled in settings)."
            )
            return
        channel_url = "{}?{}".format(
            self.url,
            urlencode(
                (
                    ("token", self.token),
                    ("channel", "#{}".format(channel or self.default_channel)),
                )
            ),
        )
        # prepare message
        message = self._prepare_message(message)

        try:
            # We need to split message into packages because of
            # openssl/urllib3 error. We are going for 12000 chars here
            # as tests showed that this is properly sent to Slack
            chunked_message = chunks(message, 12000)
            for chunk in chunked_message:
                # Sending data of type unicode behaves badly:
                # it'll get automatically encoded to some random encoding
                # you don't get to choose. All data should be encoded
                # manually by the user before it's passed to requests.
                encoded_chunk = chunk.encode("utf-8")
                response = requests.post(
                    channel_url, data=encoded_chunk, timeout=7
                )
                response.raise_for_status()
        except Exception as error:
            # Catch all network and HTTP errors raised by `requests`
            self.logger.error(
                "Slack request failed: {}".format(format_exception(error))
            )
