import click

from . import explode_repos_yaml
from . import report

@click.group()
def cli():
    """
    Tools for implementing and enforcing OEP-2.
    """
    pass

cli.add_command(explode_repos_yaml.explode)
cli.add_command(explode_repos_yaml.implode)
cli.add_command(report.cli, 'report')
