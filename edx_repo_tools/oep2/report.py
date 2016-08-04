"""
``oep2 report``: Check repositories for OEP-2 compliance.
"""

import logging

import click
import pytest

LOGGER = logging.getLogger(__name__)


@click.command()
@click.option(
    '-o', '--org',
    multiple=True,
    show_default=True,
    default=['edx', 'edx-ops'],
    help="Specify an org to check all of that orgs non-fork "
         "repositories for OEP-2 compliance",
)
@click.option(
    '-r', '--repo',
    multiple=True,
    default=None,
    help="Specify a repository to check it for OEP-2 compliance",
)
@click.option('--oep', multiple=True, default=None)
def cli(org, repo, oep):
    """
    Command-line interface specification for ``oep2 report``.
    """
    args = ['edx_repo_tools/oep2/tests', '-rxs', '-n', 'auto']

    for _org in org:
        args.extend(['--org', _org])

    for _repo in repo:
        args.extend(['--repo', _repo])

    for _oep in oep:
        args.extend(['--oep', _oep])

    pytest.main(args)
