# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import datetime
import inspect
import logging
import os
import pipes
import re
import subprocess
import sys
from importlib import import_module

from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.utils.six import text_type

# pylint: disable=E0401, E0611
from django.utils.six.moves import range

from dateutil.parser import parse as dateutil_parse

from cronman.config import app_settings

MYPY = False
if MYPY:
    from typing import Union, Text, TypeVar

    T = TypeVar("T")

logger = logging.getLogger("cronman.command")


PARAM_PATTERN = re.compile(
    "(\s*(?P<key>[\w\d_\-]*)\s*=\s*)?((?P<value>(\"[^\"]*\"|'[^']*'|[^,]*)),?)"
)


def format_exception(exception=None):
    """Convert exception into string for logging purposes."""
    exception = exception if exception is not None else sys.exc_info()[1]
    return (
        "{}: {}".format(type(exception).__name__, force_text(exception))
        if exception is not None
        else ""
    )


def config(name):
    """Retrieves config value from environment or app settings"""
    value = os.environ.get(name)
    if value is None:
        value = getattr(app_settings, name)
    return value


def cron_jobs_module_config(name, default=None):
    """Retrieves value as attribute of CRONMAN_JOBS_MODULE."""
    cron_jobs_module = config("CRONMAN_JOBS_MODULE")
    if cron_jobs_module is None:
        return default
    # AttributeError or ImportError should be loud
    value = getattr(import_module(cron_jobs_module), name)
    return default if value is None else value


def chunks(iterable, n):
    """Yield successive n-sized chunks from iterable"""
    for i in range(0, len(iterable), n):
        yield iterable[i : i + n]


def function_signature(func):
    """Formats function parameters"""
    arg_spec = inspect.getargspec(func)
    defaults = arg_spec.defaults or ()
    num_args = len(arg_spec.args)
    args = []
    for i, name in enumerate(arg_spec.args):
        # NOTE: In Python 3, unbound methods are functions so we can't use
        # `inspect.ismethod`. Instead, we use naming convention to eliminate
        # first parameter when it's a reference to current object or class.
        if i == 0 and name in ("self", "cls", "mcs"):
            continue
        try:
            default = defaults[-num_args + i]
        except IndexError:
            args.append(name)
        else:
            args.append("{}={!r}".format(name, default))
    if arg_spec.varargs:
        args.append("*{}".format(arg_spec.varargs))
    if arg_spec.keywords:
        args.append("**{}".format(arg_spec.keywords))
    return ", ".join(args)


def _parse_params_error(match_obj, message):
    """Helper to raise error in parse_params"""
    return ValueError(
        "In chars {}-{} `{}`: {}".format(
            match_obj.start(), match_obj.end(), match_obj.group(0), message
        )
    )


def parse_params(params_string):
    """Converts string of params into pair: (positional args, named args)"""
    args = []
    kwargs = {}
    match_objects = list(PARAM_PATTERN.finditer(params_string))
    for match_obj in match_objects[:-1]:  # skip empty end match
        group_dict = match_obj.groupdict()

        # Clean value:
        value = group_dict["value"].strip()
        if not value:
            raise _parse_params_error(
                match_obj, 'Implicit empty value. Use explicit `""` instead.'
            )
        if value.count('"') % 2 or value.count("'") % 2:
            raise _parse_params_error(match_obj, "Unbalanced parentheses.")
        if value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]

        key = group_dict["key"]
        if key is None:
            # Positional argument:
            if kwargs:
                raise _parse_params_error(
                    match_obj, "Positional argument after named arguments."
                )
            args.append(value)
        else:
            # Named argument:
            if not key:
                raise _parse_params_error(match_obj, "Empty named argument.")
            if key in kwargs:
                raise _parse_params_error(
                    match_obj, "Duplicated named argument."
                )
            kwargs[key] = value

    return args, kwargs


def parse_job_spec(job_spec):
    """Converts a string into pair: CronJob name, params dict"""
    try:
        name, params_string = job_spec.split(":", 1)
    except ValueError:
        name, params_string = job_spec, ""
    if params_string:
        args, kwargs = parse_params(params_string)
    else:
        args, kwargs = [], {}
    return name, args, kwargs


def bool_param(value, default=None):
    # type: (Union[bool, Text, None], T) -> Union[bool, T]
    """Coverts string param into boolean"""
    if isinstance(value, bool):
        result = value
    else:  # string
        value = "" if value is None else value.lower()
        if value in ("1", "true", "yes", "y", "on"):
            result = True
        elif value in ("0", "false", "no", "n", "off"):
            result = False
        else:
            result = default
    return result


def date_param(value, default=None):
    """Converts string param into datetime.date"""
    if isinstance(value, datetime.date):
        result = value
    else:  # string
        if value:
            result = dateutil_parse(value).date()
        else:
            result = default
    return result


def list_param(
    value,
    default=None,
    delimiter="\s+",
    strip=True,
    skip_empty=True,
    replace_map=None,
    cast=None,
):
    """Converts string param into list"""
    if isinstance(value, list):
        result = value
    else:  # string
        if not value:
            result = default or []
        else:
            result = []
            replace_map = replace_map or {}
            cast = cast or text_type
            for item in re.split(delimiter, value):
                if strip:
                    item = item.strip()
                for from_char, to_char in replace_map.items():
                    item = item.replace(from_char, to_char)
                if skip_empty and not item:
                    continue
                result.append(cast(item))
    return result


def flag_param(value, flag, flags):
    """Converts param value into boolean. When explicit value is not provided,
    checks presence of given flag in `flags`.
    List of all flags should be passed as string with values delimited by
    whitespace, ";", "," or "-".
    """
    value = bool_param(value)
    if value is None:
        flags = list_param(flags, delimiter="[\s;,\-\|]+")
        value = flag in flags
    return value


def is_accessible_dir(path):
    """Checks if given directory exists
    and current process has rwx permissions to it.
    """
    return os.access(path, os.R_OK & os.W_OK & os.X_OK) and os.path.isdir(path)


def ensure_dir(path):
    """Ensures that given directory exists
    and current process has rwx permissions to it.
    """
    if os.path.exists(path):
        ok = is_accessible_dir(path)
    else:
        try:
            os.makedirs(path)
        except OSError:
            ok = False
        else:
            ok = True
    return ok


def is_cron_process_resumed():
    """Returns True if current process was resumed, False otherwise"""
    return bool_param(os.environ.get("CRON_PROCESS_RESUMED"), default=False)


def is_cron_job_running(cron_job_class, name=None, args=None, kwargs=None):
    """Returns True if cron job is running, False otherwise"""
    from .worker import CronWorker

    worker = CronWorker()
    pid_file = worker.get_pid_file(
        cron_job_class=cron_job_class,
        name=name or cron_job_class.__name__,
        args=args or [],
        kwargs=kwargs or {},
    )
    return worker.pid_file_locked(pid_file, 1)


def spawn(*args, **kwargs):
    """Creates a subprocess that can survive process exit.
    Returns PID of the new process.
    Non-blocking call.
    """
    kwargs["stdout"] = open(os.devnull, "wb")
    kwargs["stderr"] = subprocess.STDOUT
    return subprocess.Popen(args, **kwargs).pid


def execute(*args, **kwargs):
    """Creates a subprocess and waits for it to finish.
    Returns ExecuteResult object which provides return code and output.
    Blocking call.
    """
    kwargs["stdout"] = kwargs.get("stdout", subprocess.PIPE)
    kwargs["stderr"] = kwargs.get("stderr", subprocess.PIPE)
    process = subprocess.Popen(args, **kwargs)
    output, errors = process.communicate()
    status = process.returncode
    return ExecuteResult(args, status, output, errors)


def execute_shell(command, command_args=None, **kwargs):
    """Executes shell command in a subprocess and waits for it to finish.
    Returns ExecuteResult object which provides return code and output.
    Blocking call.
    NOTICE: Should be avoided unless you need shell-specific features.
    """
    if command_args:
        if isinstance(command_args, dict):
            format_args = []
            format_kwargs = {
                key: pipes.quote(text_type(value))
                for key, value in command_args.items()
            }
        else:
            format_args = [
                pipes.quote(text_type(value)) for value in command_args
            ]
            format_kwargs = {}
        command = command.format(*format_args, **format_kwargs)
    kwargs["shell"] = True
    return execute(command, **kwargs)


def execute_pipe(*args_list, **kwargs):
    """Creates subprocess pipe and waits for it to finish.
    Returns ExecuteResult object which provides return code and output
    of the last process.
    Blocking call.
    """
    assert len(args_list) > 1
    prev_process = last_process = None
    for args in args_list:
        prev_process = last_process
        popen_kwargs = kwargs.copy()
        popen_kwargs["stdin"] = prev_process.stdout if prev_process else None
        popen_kwargs["stdout"] = subprocess.PIPE
        popen_kwargs["stderr"] = subprocess.PIPE
        last_process = subprocess.Popen(args, **popen_kwargs)
    prev_process.stdout.close()
    output, errors = last_process.communicate()
    status = last_process.returncode
    return ExecuteResult(args_list, status, output, errors)


class ExecuteResult(object):
    """Process execution results"""

    def __init__(self, args, status, output, errors):
        self.args = args
        self.status = status
        self.output = output
        self.errors = errors
        if not self.ok:
            logger.warning(
                "Command `{}` exited with status {}.".format(
                    self.command, self.status
                )
            )

    @cached_property
    def command(self):
        if self.args and not isinstance(self.args[0], (list, tuple)):
            args_list = (self.args,)
        else:
            args_list = self.args
        return " | ".join(
            " ".join(force_text(a) for a in args) for args in args_list
        )

    @property
    def ok(self):
        return self.status == 0

    def __nonzero__(self):
        return self.ok

    @property
    def output_text(self):
        return force_text(self.output)

    @property
    def errors_text(self):
        return force_text(self.errors)

    __bool__ = __nonzero__  # Python 3


class CWD(object):
    """Change working directory utility - decorator and context manager"""

    def __init__(self, new_dir):
        self.new_dir = new_dir
        self.old_dir = None

    def __call__(self, function):
        def _cwd(*args, **kwargs):
            self.change()
            try:
                return function(*args, **kwargs)
            finally:
                self.reset()

        return _cwd

    def __enter__(self):
        self.change()

    def __exit__(self, *args, **kwargs):
        self.reset()

    def change(self):
        """Changes current working directory, remembers previous value"""
        self.old_dir = os.getcwd()
        os.chdir(self.new_dir)

    def reset(self):
        """Restores previous working directory"""
        os.chdir(self.old_dir)


class TabularFormatter(object):
    """Helper to format tabular output for the console"""

    @classmethod
    def format_listing_output(
        cls, items, totals=None, vertical=False, title=None, empty_message=None
    ):
        """Formats listing results (dictionaries) as text"""
        output_lines = []
        if vertical:
            format_line = cls.format_vertical_output_line
        else:
            format_line = cls.format_horizontal_output_line
        if title:
            output_lines.append(title)
        if items:
            for item in items:
                output_lines.append(format_line(item))
            if totals:
                output_lines.append(cls.format_summary_output_line(totals))
        elif empty_message:
            output_lines.append(empty_message)
        return "\n".join(output_lines) + "\n"

    @staticmethod
    def format_horizontal_output_line(data):
        """Converts dictionary values to text separated by tab character"""
        return "\t".join(
            force_text(value)
            for key, value in data.items()
            if not key.startswith("_")
        )

    @staticmethod
    def format_vertical_output_line(data):
        """Converts dictionary to text - `<key>: <value>` pairs separated
        by new line character.
        """
        return "\n".join(
            "{}: {}".format(force_text(key), force_text(value))
            for key, value in data.items()
            if not key.startswith("_")
        )

    @staticmethod
    def format_summary_output_line(data):
        """Converts dictionary to text - `<key>: <value>` pairs separated
        by tab character.
        """
        return "\t".join(
            "{}: {}".format(force_text(key), force_text(value))
            for key, value in data.items()
        )
