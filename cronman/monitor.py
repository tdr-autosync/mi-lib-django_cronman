# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import cached_property
from django.utils.html import strip_tags
from django.utils.http import urlencode

import requests
from six.moves.html_parser import HTMLParser

from cronman.config import app_settings
from cronman.exceptions import MissingDependency
from cronman.utils import bool_param, chunks, config, format_exception

logger = logging.getLogger("cronman.command")


def _get_sentry_sdk():
    """Creates raven.Client instance configured to work with cron jobs."""
    # NOTE: this function uses settings and therefore it shouldn't be called
    #       at module level.
    try:
        sentry_sdk = __import__("sentry_sdk")
        DjangoIntegration = __import__(
            "sentry_sdk.integrations.django"
        ).integrations.django.DjangoIntegration
    except ImportError:
        raise MissingDependency(
            "Unable to import sentry_sdk. "
            "Sentry monitor requires this dependency."
        )

    for setting in (
        "CRONMAN_SENTRY_CONFIG",
        "SENTRY_CONFIG",
        "RAVEN_CONFIG",
    ):
        client_config = getattr(settings, setting, None)
        if client_config is not None:
            break
    else:
        client_config = app_settings.CRONMAN_SENTRY_CONFIG

    sentry_sdk.init(integrations=[DjangoIntegration()], **client_config)
    return sentry_sdk


class Cronitor(object):
    """Wrapper over Cronitor web API"""

    def __init__(self):
        self.logger = logger
        self.enabled = bool_param(config("CRONMAN_CRONITOR_ENABLED"))
        self.url = app_settings.CRONMAN_CRONITOR_URL

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
        self.logger = logger
        self.enabled = bool_param(config("CRONMAN_SENTRY_ENABLED"))
        self.raven_cmd = app_settings.CRONMAN_RAVEN_CMD

    @cached_property
    def _sentry_sdk(self):
        return _get_sentry_sdk()

    def capture_exception(self, exception):
        if self.enabled:
            self._sentry_sdk.capture_exception(exception)
        else:
            self.logger.debug("Sentry request ignored (disabled in settings).")


def send_errors_to_sentry(method):
    """Decorator for CronScheduler / CronWorker public methods aimed to send
    unhandled exceptions to Sentry.
    """

    def _method(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Exception as e:
            self.sentry.capture_exception(e)
            raise

    return _method


class Slack(object):
    """Wrapper over Slack web API"""

    def __init__(self):
        self.logger = logger
        self.enabled = bool_param(config("CRONMAN_SLACK_ENABLED"))
        self.url = app_settings.CRONMAN_SLACK_URL
        self.token = app_settings.CRONMAN_SLACK_TOKEN
        self.default_channel = app_settings.CRONMAN_SLACK_DEFAULT_CHANNEL

    def _prepare_message(self, message):
        # slack don't process html entities
        html_parser = HTMLParser()
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
        if not (self.url and self.token):
            raise ImproperlyConfigured(
                "CRONMAN_SLACK_URL and CRONMAN_SLACK_TOKEN are required by "
                "Slack integration. Please provide values for these settings "
                "or disable Slack integration (CRONMAN_SLACK_ENABLED = False)."
            )
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
