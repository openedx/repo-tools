"""
``oep2 report``: Check repositories for OEP-2 compliance.
"""

import logging
import pkg_resources
import sys

import click
from git.cmd import Git
import pytest

from edx_repo_tools.auth import pass_github
from .plugin import Oep2ReportPlugin

LOGGER = logging.getLogger(__name__)


@click.command(context_settings={'ignore_unknown_options': True})
@click.option(
    '--trace/--no-trace', default=False,
    help="Trace git and github interactions during reporting",
)
@click.argument(
    'pytest_args',
    nargs=-1,
    type=click.UNPROCESSED,
)
@pass_github
def cli(hub, trace, pytest_args):
    """
    Command-line interface specification for ``oep2 report``.
    """
    args = [
        '--pyargs', 'edx_repo_tools.oep2.checks',
        '-c', pkg_resources.resource_filename(__name__, 'oep2-report.ini'),
    ]

    if trace:
        args.extend(['-s', '-vvv'])
        Git.GIT_PYTHON_TRACE = True
    else:
        args.append('-q')

    args.extend(pytest_args)

    plugins = [
        Oep2ReportPlugin(hub),
    ]

    sys.exit(pytest.main(args=args, plugins=plugins))
