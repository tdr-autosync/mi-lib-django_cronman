# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import importlib
import os
import re
from distutils import log
from distutils.errors import DistutilsError

from setuptools import Command, find_packages, setup
from setuptools.command.test import test as BaseTestCommand

DJANGO_SETTINGS_MODULE = "cronman.tests.settings"


def read(*path_parts):
    """Retrieve content of a text file"""
    file_path = os.path.join(os.path.dirname(__file__), *path_parts)
    with open(file_path) as file_obj:
        return file_obj.read()


def find_version(*path_parts):
    """Retrieve current version string"""
    version_file_contents = read(*path_parts)
    version_match = re.search(
        r'^__version__ = ["\'](?P<version>[^"\']*)["\']',
        version_file_contents,
        re.M,
    )
    if not version_match:
        raise RuntimeError("Unable to find version string.")
    return version_match.group("version")


def django_setup(debug=False):
    """Set up Django using test settings module."""
    os.environ["DJANGO_SETTINGS_MODULE"] = DJANGO_SETTINGS_MODULE
    if debug:
        os.environ.setdefault("TEST_CRONMAN_LOG_LEVEL", "DEBUG")

    import django

    django.setup()


class TestCommand(BaseTestCommand):
    """Command to run unit tests (both pure-Python and Django) after in-place
    build.

    # NOTE: Pure-Python unit tests disabled.
    """

    def run_tests(self):
        # Pure-Python unit tests from `tests/*` - disabled.
        # BaseTestCommand.run_tests(self)

        # Run Django tests:

        django_setup()

        from django.test.utils import get_runner

        test_runner_class = get_runner(
            importlib.import_module(DJANGO_SETTINGS_MODULE),
            test_runner_class="django.test.runner.DiscoverRunner",
        )

        test_runner = test_runner_class(verbosity=2, interactive=True)
        failures = test_runner.run_tests(["cronman"])
        if failures:
            msg = "Django tests failed."
            self.announce(msg, log.ERROR)
            raise DistutilsError(msg)


class BaseAliasCommand(Command):
    """Setup command working as simple alias to Django's command."""

    user_options = []

    django_command = "help"

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        """Run `shell`"""
        django_setup(debug=True)

        from django.core.management import call_command

        call_command(self.django_command)


class ShellCommand(BaseAliasCommand):
    """Command to run Django's `shell`."""

    description = "run Django's `shell`."

    django_command = "shell"


class MakeMigrationsCommand(BaseAliasCommand):
    """Command to run Django's `makemigrations`."""

    description = "run Django's `makemigrations`."

    django_command = "makemigrations"


class MigrateCommand(BaseAliasCommand):
    """Command to run Django's `migrate`."""

    description = "run Django's `migrate`."

    django_command = "migrate"


setup(
    name="django-cronman",
    version=find_version("cronman", "version.py"),
    description="Cron management app for Django",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    url="https://github.com/unhaggle/django-cronman",
    author="Unhaggle Inc.",
    author_email="",
    packages=find_packages(),
    install_requires=[
        "croniter < 0.4",
        "django < 2.0",
        "python-dateutil < 2.7",
        "requests >= 2.1",
        "typing",
    ],
    include_package_data=True,
    tests_require=["mock", "raven < 5.33", "redis < 2.11"],
    extras_require={"redis": ["redis < 2.11"], "sentry": ["raven < 5.33"]},
    cmdclass={
        "test": TestCommand,
        "shell": ShellCommand,
        "makemigrations": MakeMigrationsCommand,
        "migrate": MigrateCommand,
    },
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 2.7",
        "License :: OSI Approved :: BSD License",
        "Framework :: Django",
        "Framework :: Django :: 1.11",
        "Environment :: Web Environment",
        "Operating System :: POSIX",
        "Topic :: Utilities",
    ],
)
