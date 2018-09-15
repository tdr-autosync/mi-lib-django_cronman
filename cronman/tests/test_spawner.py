# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import errno
import platform

import mock

from cronman.spawner import CronSpawner
from cronman.tests.base import (
    TEST_CRONMAN_DATA_DIR,
    BaseCronTestCase,
    expected_worker_env,
    mock_environ,
    override_cron_settings,
)

SYSTEM_NAME = platform.node()


class CronSpawnerTestCase(BaseCronTestCase):
    """Tests for CronSpawner class"""

    @override_cron_settings()
    def test_get_worker_env(self):
        """Test for CronSpawner.get_worker_env method"""
        self.assertDictContainsSubset(
            {
                "CRONMAN_DATA_DIR": TEST_CRONMAN_DATA_DIR,
                "CRONMAN_CRONITOR_ENABLED": "0",
            },
            CronSpawner().get_worker_env(),
        )

    @mock.patch("cronman.spawner.spawn")
    @mock.patch("cronman.spawner.time.sleep")
    def test_start_ok(self, mock_sleep, mock_spawn):
        """Test for CronSpawner.start_worker method - OK"""
        spawner = CronSpawner()
        spawner.slack = mock.MagicMock()
        spawner.logger = mock.MagicMock()

        spawner.start_worker("Sleep:seconds=1")

        mock_sleep.assert_not_called()
        self.assertEqual(mock_spawn.call_count, 1)
        self.assertFalse(spawner.memory_error_occurred)

    @mock.patch(
        "cronman.spawner.spawn",
        side_effect=OSError(errno.ENOMEM, "Cannot allocate memory"),
    )
    @mock.patch("cronman.spawner.time.sleep")
    def test_start_worker_out_of_memory(self, mock_sleep, mock_spawn):
        """Test for CronSpawner.start_worker method - OOM error case"""
        spawner = CronSpawner()
        spawner.slack = mock.MagicMock()
        spawner.logger = mock.MagicMock()

        spawner.start_worker("Sleep:seconds=1")

        spawner.slack.post.assert_has_calls(
            [
                mock.call(
                    "[{}] "
                    "RuntimeError: "
                    "Unable to start a worker process "
                    "for Sleep:seconds=1 due to Out-Of-Memory error.".format(
                        SYSTEM_NAME
                    )
                )
            ]
        )
        spawner.logger.warning.assert_has_calls(
            [
                mock.call(
                    "RuntimeError: "
                    "Unable to start a worker process "
                    "for Sleep:seconds=1 due to Out-Of-Memory error."
                )
            ]
        )
        mock_sleep.assert_called_once_with(spawner.wait_for_memory)
        self.assertEqual(mock_spawn.call_count, 2)
        self.assertTrue(spawner.memory_error_occurred)

    @mock.patch(
        "cronman.spawner.spawn",
        side_effect=OSError(errno.ENOMEM, "Cannot allocate memory"),
    )
    @mock.patch("cronman.spawner.time.sleep")
    def test_start_worker_out_of_memory_again(self, mock_sleep, mock_spawn):
        """Test for CronSpawner.start_worker method - OOM error case (again).
        """
        spawner = CronSpawner()
        spawner.slack = mock.MagicMock()
        spawner.logger = mock.MagicMock()
        spawner.memory_error_occurred = True

        spawner.start_worker("Sleep:seconds=1")

        spawner.slack.post.assert_has_calls(
            [
                mock.call(
                    "[{}] "
                    "RuntimeError: "
                    "Unable to start a worker process "
                    "for Sleep:seconds=1 due to Out-Of-Memory error.".format(
                        SYSTEM_NAME
                    )
                )
            ]
        )
        spawner.logger.warning.assert_has_calls(
            [
                mock.call(
                    "RuntimeError: "
                    "Unable to start a worker process "
                    "for Sleep:seconds=1 due to Out-Of-Memory error."
                )
            ]
        )
        mock_sleep.assert_not_called()
        self.assertEqual(mock_spawn.call_count, 1)
        self.assertTrue(spawner.memory_error_occurred)

    @mock.patch(
        "cronman.spawner.spawn",
        side_effect=OSError(errno.EPERM, "Permission Denied"),
    )
    @mock.patch("cronman.spawner.time.sleep")
    def test_start_with_os_error(self, mock_sleep, mock_spawn):
        """Test for CronSpawner.start_worker method - other OSError case"""
        spawner = CronSpawner()
        spawner.slack = mock.MagicMock()
        spawner.logger = mock.MagicMock()

        with self.assertRaises(OSError):
            spawner.start_worker("Sleep:seconds=1")

        mock_sleep.assert_not_called()
        self.assertEqual(mock_spawn.call_count, 1)
        self.assertFalse(spawner.memory_error_occurred)

    @mock.patch("cronman.spawner.spawn", side_effect=RuntimeError)
    @mock.patch("cronman.spawner.time.sleep")
    def test_start_with_other_error(self, mock_sleep, mock_spawn):
        """Test for CronSpawner.start_worker method - other exception type
        case"""
        spawner = CronSpawner()
        spawner.slack = mock.MagicMock()
        spawner.logger = mock.MagicMock()

        with self.assertRaises(RuntimeError):
            spawner.start_worker("Sleep:seconds=1")

        mock_sleep.assert_not_called()
        self.assertEqual(mock_spawn.call_count, 1)
        self.assertFalse(spawner.memory_error_occurred)

    @override_cron_settings()
    @mock.patch("cronman.spawner.spawn")
    @mock.patch("cronman.spawner.os.environ.copy", mock_environ)
    @mock.patch(
        "cronman.spawner.sys.argv", ["manage.py", "cron_scheduler", "run"]
    )
    @mock.patch("cronman.spawner.sys.executable", "/bin/python")
    def test_start_worker_os_environ_passed(self, mock_spawn):
        """Test that CronSpawner.start_worker passes converted environment
        variables to child processes.
        """
        spawner = CronSpawner()
        spawner.start_worker("Sleep:seconds=1,path=/tmp/sleep.txt")
        mock_spawn.assert_called_once_with(
            "/bin/python",
            "manage.py",
            "cron_worker",
            "run",
            "Sleep:seconds=1,path=/tmp/sleep.txt",
            env=expected_worker_env(),
        )

    @override_cron_settings(CRONMAN_RAVEN_CMD=None)
    @mock.patch("cronman.spawner.spawn")
    @mock.patch(
        "cronman.spawner.sys.argv", ["manage.py", "cron_scheduler", "run"]
    )
    @mock.patch("cronman.spawner.sys.executable", "/bin/python")
    def test_start_worker_no_raven_cmd_no_settings(self, mock_spawn):
        """Test for CronSpawner.start_worker method
         - CRONMAN_RAVEN_CMD defined, no --settings passed
        """
        spawner = CronSpawner()
        spawner.start_worker("Sleep:seconds=10")
        mock_spawn.assert_called_once_with(
            "/bin/python",
            "manage.py",
            "cron_worker",
            "run",
            "Sleep:seconds=10",
            env=spawner.get_worker_env(),
        )

    @override_cron_settings(CRONMAN_RAVEN_CMD=None)
    @mock.patch("cronman.spawner.spawn")
    @mock.patch(
        "cronman.spawner.sys.argv",
        ["manage.py", "cron_scheduler", "run", "--settings=test"],
    )
    @mock.patch("cronman.spawner.sys.executable", "/bin/python")
    def test_start_worker_no_raven_cmd_with_settings(self, mock_spawn):
        """Test for CronSpawner.start_worker method
         - CRONMAN_RAVEN_CMD undefined, --settings passed
        """
        spawner = CronSpawner()
        spawner.start_worker("Sleep:seconds=10")
        mock_spawn.assert_called_once_with(
            "/bin/python",
            "manage.py",
            "cron_worker",
            "run",
            "Sleep:seconds=10",
            "--settings=test",
            env=spawner.get_worker_env(),
        )

    @override_cron_settings(CRONMAN_RAVEN_CMD=None)
    @mock.patch("cronman.spawner.spawn")
    @mock.patch(
        "cronman.spawner.sys.argv", ["manage.py", "cron_scheduler", "run"]
    )
    @mock.patch("cronman.spawner.sys.executable", "/bin/python")
    def test_start_worker_no_raven_cmd_no_settings_quoted(self, mock_spawn):
        """Test for CronSpawner.start_worker method
         - CRONMAN_RAVEN_CMD defined, no --settings passed, quoted param
        """
        spawner = CronSpawner()
        spawner.start_worker('Sleep:seconds=10,quoted="This is a test"')
        mock_spawn.assert_called_once_with(
            "/bin/python",
            "manage.py",
            "cron_worker",
            "run",
            'Sleep:seconds=10,quoted="This is a test"',
            env=spawner.get_worker_env(),
        )

    @override_cron_settings(CRONMAN_RAVEN_CMD="/usr/bin/raven-cmd")
    @mock.patch("cronman.spawner.spawn")
    @mock.patch(
        "cronman.spawner.sys.argv", ["manage.py", "cron_scheduler", "run"]
    )
    @mock.patch("cronman.spawner.sys.executable", "/bin/python")
    def test_start_worker_with_raven_cmd_no_settings(self, mock_spawn):
        """Test for CronSpawner.start_worker method
         - CRONMAN_RAVEN_CMD defined, no --settings passed
        """
        spawner = CronSpawner()
        spawner.start_worker("Sleep:seconds=10")
        mock_spawn.assert_called_once_with(
            "/usr/bin/raven-cmd",
            "-c",
            "/bin/python manage.py cron_worker run Sleep:seconds=10",
            env=spawner.get_worker_env(),
        )

    @override_cron_settings(CRONMAN_RAVEN_CMD="/usr/bin/raven-cmd")
    @mock.patch("cronman.spawner.spawn")
    @mock.patch(
        "cronman.spawner.sys.argv",
        ["manage.py", "cron_scheduler", "run", "--settings=test"],
    )
    @mock.patch("cronman.spawner.sys.executable", "/bin/python")
    def test_start_worker_with_raven_cmd_with_settings(self, mock_spawn):
        """Test for CronSpawner.start_worker method
         - CRONMAN_RAVEN_CMD defined, --settings passed
        """
        spawner = CronSpawner()
        spawner.start_worker("Sleep:seconds=10")
        mock_spawn.assert_called_once_with(
            "/usr/bin/raven-cmd",
            "-c",
            "/bin/python manage.py cron_worker run Sleep:seconds=10 "
            "--settings=test",
            env=spawner.get_worker_env(),
        )

    @override_cron_settings(CRONMAN_RAVEN_CMD="/usr/bin/raven-cmd")
    @mock.patch("cronman.spawner.spawn")
    @mock.patch(
        "cronman.spawner.sys.argv", ["manage.py", "cron_scheduler", "run"]
    )
    @mock.patch("cronman.spawner.sys.executable", "/bin/python")
    def test_start_worker_with_raven_cmd_no_settings_quoted(self, mock_spawn):
        """Test for CronSpawner.start_worker method
         - CRONMAN_RAVEN_CMD defined, no --settings passed, quoted param
        """
        spawner = CronSpawner()
        spawner.start_worker('Sleep:seconds=10,quoted="This is a test"')
        mock_spawn.assert_called_once_with(
            "/usr/bin/raven-cmd",
            "-c",
            "/bin/python manage.py cron_worker run "
            "\"Sleep:seconds=10,quoted='This is a test'\"",
            env=spawner.get_worker_env(),
        )

    # Starting workers with CPU/IO priority

    @override_cron_settings(CRONMAN_RAVEN_CMD=None)
    @mock.patch("cronman.spawner.spawn")
    @mock.patch(
        "cronman.spawner.sys.argv", ["manage.py", "cron_scheduler", "run"]
    )
    @mock.patch("cronman.spawner.sys.executable", "/bin/python")
    def test_start_worker_nice_ionice_no_raven_cmd_no_settings(
        self, mock_spawn
    ):
        """Test for CronSpawner.start_worker method
         - CRONMAN_RAVEN_CMD defined, no --settings passed, nice, ionice
        """
        spawner = CronSpawner()
        spawner.start_worker("LowestCPUIOSleep:seconds=10")
        mock_spawn.assert_called_once_with(
            "nice",
            "-n",
            "19",
            "ionice",
            "-c",
            "2",
            "-n",
            "7",
            "/bin/python",
            "manage.py",
            "cron_worker",
            "run",
            "LowestCPUIOSleep:seconds=10",
            env=spawner.get_worker_env(),
        )

    @override_cron_settings(CRONMAN_RAVEN_CMD="/usr/bin/raven-cmd")
    @mock.patch("cronman.spawner.spawn")
    @mock.patch(
        "cronman.spawner.sys.argv", ["manage.py", "cron_scheduler", "run"]
    )
    @mock.patch("cronman.spawner.sys.executable", "/bin/python")
    def test_start_worker_ionice_with_raven_cmd_no_settings_quoted(
        self, mock_spawn
    ):
        """Test for CronSpawner.start_worker method
         - CRONMAN_RAVEN_CMD defined, no --settings passed, quoted param, ionice
        """
        spawner = CronSpawner()
        spawner.start_worker('IdleIOSleep:seconds=10,quoted="This is a test"')
        mock_spawn.assert_called_once_with(
            "/usr/bin/raven-cmd",
            "-c",
            "ionice -c 3 /bin/python manage.py cron_worker run "
            "\"IdleIOSleep:seconds=10,quoted='This is a test'\"",
            env=spawner.get_worker_env(),
        )

    @override_cron_settings(CRONMAN_RAVEN_CMD="/usr/bin/raven-cmd")
    @mock.patch("cronman.spawner.spawn")
    @mock.patch(
        "cronman.spawner.sys.argv", ["manage.py", "cron_scheduler", "run"]
    )
    @mock.patch("cronman.spawner.sys.executable", "/bin/python")
    def test_start_worker_nice_with_raven_cmd_no_settings(self, mock_spawn):
        """Test for CronSpawner.start_worker method
         - CRONMAN_RAVEN_CMD defined, no --settings passed, nice
        """
        spawner = CronSpawner()
        spawner.start_worker("LowCPUSleep:seconds=10")
        mock_spawn.assert_called_once_with(
            "/usr/bin/raven-cmd",
            "-c",
            "nice -n 10 /bin/python manage.py cron_worker run "
            "LowCPUSleep:seconds=10",
            env=spawner.get_worker_env(),
        )
