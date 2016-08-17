"""
``oep2 report``: Check repositories for OEP-2 compliance.
"""

import logging
import pkg_resources

import click
from git.cmd import Git
import pytest

LOGGER = logging.getLogger(__name__)


@click.command()
@click.option(
    '-o', '--org',
    multiple=True,
    show_default=True,
    default=[],
    help="Specify an org to check all of that orgs non-fork "
         "repositories for OEP-2 compliance",
)
@click.option(
    '-r', '--repo',
    multiple=True,
    default=None,
    help="Specify a repository to check it for OEP-2 compliance",
)
@click.option(
    '--oep',
    multiple=True, default=None,
    help="List of OEPs to check for explicit specification of compliance",
)
@click.option(
    '-n', '--num-processes',
    default=1,
    help="How many procesess to use while checking repositories",
)
@click.option(
    '--trace/--no-trace', default=False,
    help="Trace git and github interactions during reporting",
)
@click.option(
    "--checkout-root",
    default=".oep2-workspace",
    help="Where to check out repos that are being checked for oep2 compliance",
)
# N.B. We don't use @pass_github here because there isn't a nice way to pass
# the resulting `hub` object into the pytest tests.
@click.option(
    '--username',
    help='Specify the user to log in to GitHub with',
)
@click.option('--password', help='Password to log in to GitHub with')
@click.option(
    '--token',
    help='Personal access token to log in to GitHub with',
)
def cli(org, repo, oep, num_processes, trace, checkout_root, username, password, token):
    """
    Command-line interface specification for ``oep2 report``.
    """
    args = [
        '--pyargs', 'edx_repo_tools.oep2.checks',
        '-c', pkg_resources.resource_filename(__name__, 'oep2-report.ini'),
        '--checkout-root', checkout_root,
    ]

    if trace:
        args.extend(['-s', '-vvv'])
        Git.GIT_PYTHON_TRACE = True
    else:
        args.append('-q')

    if username is not None:
        args.extend(['--username', username])

    if token is not None:
        args.extend(['--token', token])

    if password is not None:
        args.extend(['--password', password])

    if num_processes != 1:
        args.extend(['-n', num_processes])

    for _org in org:
        args.extend(['--org', _org])

    for _repo in repo:
        args.extend(['--repo', _repo])

    for _oep in oep:
        args.extend(['--oep', _oep])

    click.secho("py.test " + " ".join(args))

    pytest.main(args)
