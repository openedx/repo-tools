"""
``oep2 implode``: aggregate many openedx.yaml files.
"""

import click
from github3.exceptions import NotFoundError
import logging
import yaml

from edx_repo_tools.auth import pass_github
from edx_repo_tools.data import iter_openedx_yaml


logging.basicConfig()
LOGGER = logging.getLogger(__name__)


@click.command()
@pass_github
@click.option('--org', multiple=True, default=['edx', 'edx-ops', 'edx-solutions',])
@click.option(
    '--branch',
    multiple=True,
    default=None,
    help="The branch(es) to examine for openedx.yaml files. If more than one, "
         "the first found will be used."
)
def implode(hub, org, branch):
    """
    Implode all openedx.yaml files, and print the results as formatted output.
    """
    data = {
        repo.full_name: openedx_yaml
        for repo, openedx_yaml
        in iter_openedx_yaml(hub, org, branch)
    }
    click.echo(yaml.safe_dump(data, encoding=None, indent=4))
