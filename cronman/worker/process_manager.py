# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import errno
import functools
import logging
import os
import signal
import subprocess

from django.utils.encoding import force_text

logger = logging.getLogger("cronman.command.cron_worker")


def pid_required(otherwise):
    """Decorator for ProcessManager methods to provide alternative result
    when PID is not available.
    """

    def decorator(method):
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            if self.pid is None:
                result = otherwise
            else:
                result = method(self, *args, **kwargs)
            return result

        return wrapper

    return decorator


class ProcessManager(object):
    """Wrapper over PID value, communicates with other processes through
    signals.
    """

    def __init__(self, pid):
        self.pid = pid
        self.logger = logger

    @pid_required(otherwise=False)  # Same as `errno.ESRCH`
    def _kill(self, sig):
        """Sends signal to the process"""
        try:
            os.kill(self.pid, sig)
        except OSError as e:
            if e.errno == errno.ESRCH:
                result = False
            else:  # Process exists but access is denied
                result = None
        else:
            result = True
        return result

    def exists(self):
        """Check if PID is assigned to existing process"""
        return self._kill(0)

    def alive(self):
        """Check if PID is assigned to existing ALIVE process"""
        process_exists = self.exists()
        if process_exists:
            if "Z" in self.status():
                self.logger.warning(
                    "PID {} belongs to zombie process. "
                    "This means that parent process is still alive, while "
                    "child process have been killed. This is OK during tests, "
                    "but should never happen in real life.".format(self.pid)
                )
                is_alive = False
            else:
                is_alive = True
        else:
            is_alive = process_exists  # False or None (no access)
        return is_alive

    def terminate(self):
        """Terminates the process"""
        return self._kill(signal.SIGTERM)

    def kill(self):
        """Kills the process"""
        return self._kill(signal.SIGKILL)

    @pid_required(otherwise="")
    def status(self):
        """Retrieves status of the process using `ps` command"""
        try:
            stat = force_text(
                subprocess.check_output(
                    ["ps", "-p", str(self.pid), "-o", "stat="]
                ).strip()
            )
        except subprocess.CalledProcessError:
            stat = ""
        return stat
