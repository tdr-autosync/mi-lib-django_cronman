# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import signal

import mock

from cronman.tests.base import BaseCronTestCase
from cronman.worker.signal_notifier import SignalNotifier


class SignalNotifierTestCase(BaseCronTestCase):
    """Tests for SignalNotifier class"""

    def test_context_manager_handlers_assignment(self):
        """Test for context manager: signal handlers (dis)assignment"""
        # `signal.default_int_handler` may be overwritten by unittests:
        default_int_handler = signal.getsignal(signal.SIGINT)
        default_term_handler = signal.getsignal(signal.SIGTERM)
        with SignalNotifier("TestCronJob") as signal_notifier:
            self.assertEqual(
                signal.getsignal(signal.SIGINT),
                signal_notifier.notify_and_quit,
            )
            self.assertEqual(
                signal.getsignal(signal.SIGTERM),
                signal_notifier.notify_and_quit,
            )
        self.assertEqual(signal.getsignal(signal.SIGINT), default_int_handler)
        self.assertEqual(
            signal.getsignal(signal.SIGTERM), default_term_handler
        )

    @mock.patch("cronman.worker.signal_notifier.sys.exit")
    def test_handle_sigint(self, mock_exit):
        """Test for `notify_and_quit`, case: SIGINT received"""
        signal_notifier = SignalNotifier("TestCronJob")
        signal_notifier.logger = mock.MagicMock()
        signal_notifier.slack = mock.MagicMock()

        signal_notifier.notify_and_quit(signal.SIGINT, None)

        mock_exit.assert_called_once_with(signal.SIGINT)
        signal_notifier.logger.warning.assert_has_calls(
            [mock.call('Cron job "TestCronJob" killed by SIGINT.')]
        )
        signal_notifier.slack.post.assert_called_once_with(
            'Cron job "TestCronJob" killed by SIGINT.'
        )

    @mock.patch("cronman.worker.signal_notifier.sys.exit")
    def test_handle_sigterm(self, mock_exit):
        """Test for `notify_and_quit`, case: SIGTERM received"""
        signal_notifier = SignalNotifier("TestCronJob")
        signal_notifier.logger = mock.MagicMock()
        signal_notifier.slack = mock.MagicMock()

        signal_notifier.notify_and_quit(signal.SIGTERM, None)

        mock_exit.assert_called_once_with(signal.SIGTERM)
        signal_notifier.logger.warning.assert_has_calls(
            [mock.call('Cron job "TestCronJob" killed by SIGTERM.')]
        )
        signal_notifier.slack.post.assert_called_once_with(
            'Cron job "TestCronJob" killed by SIGTERM.'
        )
