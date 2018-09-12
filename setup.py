# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4

from __future__ import unicode_literals

import importlib
import os
import re
from distutils import log
from distutils.errors import DistutilsError

from setuptools import find_packages, setup
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


def django_setup():
    """Set up Django using test settings module."""
    os.environ["DJANGO_SETTINGS_MODULE"] = DJANGO_SETTINGS_MODULE

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


setup(
    name="django-cronman",
    version=find_version("cronman", "version.py"),
    description="Cron management app for Django",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    url="https://github.com/unhaggle/django-cronman",
    author="Motoinsight",
    author_email="",
    packages=find_packages(),
    install_requires=[
        "croniter < 0.4",
        "django < 2.0",
        "geopy < 1.1",
        "python-dateutil < 2.7",
        "raven < 5.33",
        "redis < 2.11",
        "requests >= 2.1",
        "typing",
    ],
    include_package_data=True,
    tests_require=["mock"],
    cmdclass={"test": TestCommand},
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 2",
        "License :: OSI Approved :: BSD License",
        "Framework :: Django",
        "Framework :: Django :: 1.9",
        "Environment :: Web Environment",
        "Operating System :: POSIX",
        "Topic :: Utilities",
    ],
)
