# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

from django.utils.encoding import force_bytes

import mock
import requests

from cronman.monitor import Cronitor, Slack
from cronman.tests.base import BaseCronTestCase, override_cron_settings


class CronitorTestCase(BaseCronTestCase):
    """Tests for Cronitor class"""

    @override_cron_settings(
        CRONMAN_CRONITOR_URL="https://cronitor.link/{cronitor_id}/{end_point}",
        CRONMAN_CRONITOR_ENABLED=False,
    )
    @mock.patch("cronman.monitor.requests.head")
    def test_run_disabled(self, mock_head):
        """Test for `run` method, case: Cronitor disabled"""
        cronitor = Cronitor()
        cronitor.logger = mock.MagicMock()
        cronitor.run("cRoNiD")
        mock_head.assert_not_called()
        cronitor.logger.warning.assert_has_calls(
            [mock.call("Cronitor request ignored (disabled in settings).")]
        )

    @override_cron_settings(
        CRONMAN_CRONITOR_URL="https://cronitor.link/{cronitor_id}/{end_point}",
        CRONMAN_CRONITOR_ENABLED=True,
    )
    @mock.patch("cronman.monitor.requests.head")
    def test_run_enabled(self, mock_head):
        """Test for `run` method, case: Cronitor enabled"""
        cronitor = Cronitor()
        cronitor.logger = mock.MagicMock()
        cronitor.run("cRoNiD")
        mock_head.assert_called_once_with(
            "https://cronitor.link/cRoNiD/run", params=None, timeout=10
        )

    @override_cron_settings(
        CRONMAN_CRONITOR_URL="https://cronitor.link/{cronitor_id}/{end_point}",
        CRONMAN_CRONITOR_ENABLED=True,
    )
    @mock.patch(
        "cronman.monitor.requests.head",
        side_effect=requests.ConnectTimeout("msg"),
    )
    def test_run_failed(self, mock_head):
        """Test for `run` method, case: Cronitor enabled, request failed"""
        cronitor = Cronitor()
        cronitor.logger = mock.MagicMock()
        cronitor.run("cRoNiD")
        mock_head.assert_called_once_with(
            "https://cronitor.link/cRoNiD/run", params=None, timeout=10
        )
        cronitor.logger.warning.assert_has_calls(
            [
                mock.call(
                    "Cronitor request failed: "
                    "https://cronitor.link/cRoNiD/run "
                    "ConnectTimeout: msg"
                )
            ]
        )

    @override_cron_settings(
        CRONMAN_CRONITOR_URL="https://cronitor.link/{cronitor_id}/{end_point}",
        CRONMAN_CRONITOR_ENABLED=False,
    )
    @mock.patch("cronman.monitor.requests.head")
    def test_complete_disabled(self, mock_head):
        """Test for `complete` method, case: Cronitor disabled"""
        cronitor = Cronitor()
        cronitor.logger = mock.MagicMock()
        cronitor.complete("cRoNiD")
        mock_head.assert_not_called()
        cronitor.logger.warning.assert_has_calls(
            [mock.call("Cronitor request ignored (disabled in settings).")]
        )

    @override_cron_settings(
        CRONMAN_CRONITOR_URL="https://cronitor.link/{cronitor_id}/{end_point}",
        CRONMAN_CRONITOR_ENABLED=True,
    )
    @mock.patch("cronman.monitor.requests.head")
    def test_complete_enabled(self, mock_head):
        """Test for `complete` method, case: Cronitor enabled"""
        cronitor = Cronitor()
        cronitor.logger = mock.MagicMock()
        cronitor.complete("cRoNiD")
        mock_head.assert_called_once_with(
            "https://cronitor.link/cRoNiD/complete", params=None, timeout=10
        )

    @override_cron_settings(
        CRONMAN_CRONITOR_URL="https://cronitor.link/{cronitor_id}/{end_point}",
        CRONMAN_CRONITOR_ENABLED=True,
    )
    @mock.patch(
        "cronman.monitor.requests.head",
        side_effect=requests.ConnectTimeout("msg"),
    )
    def test_complete_failed(self, mock_head):
        """Test for `complete` method, case: Cronitor enabled, request failed
        """
        cronitor = Cronitor()
        cronitor.logger = mock.MagicMock()
        cronitor.complete("cRoNiD")
        mock_head.assert_called_once_with(
            "https://cronitor.link/cRoNiD/complete", params=None, timeout=10
        )
        cronitor.logger.warning.assert_has_calls(
            [
                mock.call(
                    "Cronitor request failed: "
                    "https://cronitor.link/cRoNiD/complete "
                    "ConnectTimeout: msg"
                )
            ]
        )

    @override_cron_settings(
        CRONMAN_CRONITOR_URL="https://cronitor.link/{cronitor_id}/{end_point}",
        CRONMAN_CRONITOR_ENABLED=False,
    )
    @mock.patch("cronman.monitor.requests.head")
    def test_fail_disabled(self, mock_head):
        """Test for `fail` method, case: Cronitor disabled"""
        cronitor = Cronitor()
        cronitor.logger = mock.MagicMock()
        cronitor.fail("cRoNiD", msg="RuntimeError: test message")
        mock_head.assert_not_called()
        cronitor.logger.warning.assert_has_calls(
            [mock.call("Cronitor request ignored (disabled in settings).")]
        )

    @override_cron_settings(
        CRONMAN_CRONITOR_URL="https://cronitor.link/{cronitor_id}/{end_point}",
        CRONMAN_CRONITOR_ENABLED=True,
    )
    @mock.patch("cronman.monitor.requests.head")
    def test_fail_enabled(self, mock_head):
        """Test for `fail` method, case: Cronitor enabled"""
        cronitor = Cronitor()
        cronitor.logger = mock.MagicMock()
        cronitor.fail("cRoNiD", msg="RuntimeError: test message")
        mock_head.assert_called_once_with(
            "https://cronitor.link/cRoNiD/fail",
            params={"msg": "RuntimeError: test message"},
            timeout=10,
        )

    @override_cron_settings(
        CRONMAN_CRONITOR_URL="https://cronitor.link/{cronitor_id}/{end_point}",
        CRONMAN_CRONITOR_ENABLED=True,
    )
    @mock.patch(
        "cronman.monitor.requests.head",
        side_effect=requests.ConnectTimeout("msg"),
    )
    def test_fail_failed(self, mock_head):
        """Test for `fail` method, case: Cronitor enabled, request failed
        """
        cronitor = Cronitor()
        cronitor.logger = mock.MagicMock()
        cronitor.fail("cRoNiD", msg="RuntimeError: test message")
        mock_head.assert_called_once_with(
            "https://cronitor.link/cRoNiD/fail",
            params={"msg": "RuntimeError: test message"},
            timeout=10,
        )
        cronitor.logger.warning.assert_has_calls(
            [
                mock.call(
                    "Cronitor request failed: "
                    "https://cronitor.link/cRoNiD/fail "
                    "ConnectTimeout: msg"
                )
            ]
        )


class SlackTestCase(BaseCronTestCase):
    """Tests for Slack class"""

    @override_cron_settings(
        CRONMAN_SLACK_URL="https://fake-chat.slack.com/services/hooks/slackbot",
        CRONMAN_SLACK_TOKEN="sLaCkTokEn",
        CRONMAN_SLACK_DEFAULT_CHANNEL="cronitor",
        CRONMAN_SLACK_ENABLED=False,
    )
    @mock.patch("cronman.monitor.requests.post")
    def test_post_disabled(self, mock_post):
        """Test for `post` method, case: Slack disabled"""
        slack = Slack()
        slack.logger = mock.MagicMock()
        slack.post("This is a test!")
        mock_post.assert_not_called()
        slack.logger.warning.assert_has_calls(
            [mock.call("Slack request ignored (disabled in settings).")]
        )

    @override_cron_settings(
        CRONMAN_SLACK_URL="https://fake-chat.slack.com/services/hooks/slackbot",
        CRONMAN_SLACK_TOKEN="sLaCkTokEn",
        CRONMAN_SLACK_DEFAULT_CHANNEL="cronitor",
        CRONMAN_SLACK_ENABLED=True,
    )
    @mock.patch("cronman.monitor.requests.post")
    def test_post_enabled(self, mock_post):
        """Test for `post` method, case: Slack enabled"""
        slack = Slack()
        slack.logger = mock.MagicMock()
        slack.post("This is a test!")
        mock_post.assert_called_once_with(
            "https://fake-chat.slack.com/services/hooks/slackbot?"
            "token=sLaCkTokEn&channel=%23cronitor",
            data=force_bytes("This is a test!"),
            timeout=7,
        )

    @override_cron_settings(
        CRONMAN_SLACK_URL="https://fake-chat.slack.com/services/hooks/slackbot",
        CRONMAN_SLACK_TOKEN="sLaCkTokEn",
        CRONMAN_SLACK_DEFAULT_CHANNEL="cronitor",
        CRONMAN_SLACK_ENABLED=True,
    )
    @mock.patch("cronman.monitor.requests.post")
    def test_post_enabled_custom_channel(self, mock_post):
        """Test for `post` method, case: Slack enabled, custom channel"""
        slack = Slack()
        slack.logger = mock.MagicMock()
        slack.post("This is a test!", channel="dev")
        mock_post.assert_called_once_with(
            "https://fake-chat.slack.com/services/hooks/slackbot?"
            "token=sLaCkTokEn&channel=%23dev",
            data=force_bytes("This is a test!"),
            timeout=7,
        )

    @override_cron_settings(
        CRONMAN_SLACK_URL="https://fake-chat.slack.com/services/hooks/slackbot",
        CRONMAN_SLACK_TOKEN="sLaCkTokEn",
        CRONMAN_SLACK_DEFAULT_CHANNEL="cronitor",
        CRONMAN_SLACK_ENABLED=True,
    )
    @mock.patch(
        "cronman.monitor.requests.post",
        side_effect=requests.ConnectTimeout("msg"),
    )
    def test_post_failed(self, mock_post):
        """Test for `post` method, case: Slack enabled, request failed"""
        slack = Slack()
        slack.logger = mock.MagicMock()
        slack.post("This is a test!")
        mock_post.assert_called_once_with(
            "https://fake-chat.slack.com/services/hooks/slackbot?"
            "token=sLaCkTokEn&channel=%23cronitor",
            data=force_bytes("This is a test!"),
            timeout=7,
        )
        slack.logger.error.assert_has_calls(
            [mock.call("Slack request failed: ConnectTimeout: msg")]
        )
