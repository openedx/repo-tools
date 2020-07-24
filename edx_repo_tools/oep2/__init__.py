"""
Top-level definition of the ``oep2`` commandline tool.
"""

import click

from . import explode_repos_yaml
from .report.cli import cli as report_cli


def _cli():
    cli(auto_envvar_prefix="OEP2")


@click.group()
def cli():
    """
    Tools for implementing and enforcing OEP-2.
    """
    pass

cli.add_command(explode_repos_yaml.implode)
cli.add_command(report_cli, 'report')
