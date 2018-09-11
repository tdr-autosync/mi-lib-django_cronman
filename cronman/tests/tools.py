# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import collections
import re

from django.core.management import call_command

RESULT_PATTERN = re.compile(
    "(?P<status>[A-Z]+): Processed (?P<job_spec>[\s\S]*)"
)
EXCEPTION_PATTERN = re.compile(
    "(?P<exc_class_name>[\w\d+]+): (?P<exc_message>[\s\S]*)"
)


CronWorkerRunResult = collections.namedtuple(
    "CronWorkerRunResult",
    ["output", "status", "exc_class_name", "exc_message", "ok"],
)


def call_worker(job_spec):
    """Calls command `cron_worker run <job_spec>` and parses the output"""
    output = call_command("cron_worker", "run", job_spec)
    status = exc_class_name = exc_message = None
    if output:
        result_match = RESULT_PATTERN.match(output)
        if result_match:
            status = result_match.group("status")
        else:
            exc_match = EXCEPTION_PATTERN.match(output)
            if exc_match:
                exc_class_name = exc_match.group("exc_class_name")
                exc_message = exc_match.group("exc_message")
    ok = status == "OK"
    return CronWorkerRunResult(output, status, exc_class_name, exc_message, ok)
