"""
``oep2 report``: Check repositories for OEP-2 compliance.
"""

import logging
import os.path
import pkg_resources

import click
import pytest
import yaml
from edx_repo_tools.auth import login_github

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
def cli(org, repo, oep, num_processes):
    """
    Command-line interface specification for ``oep2 report``.
    """
    args = [
        '-q',
        '--pyargs', 'edx_repo_tools.oep2.checks',
        '-c', pkg_resources.resource_filename(__name__, 'oep2-report.ini')
    ]

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


def pytest_addoption(parser):
    """
    Add options to py.test
    """
    group = parser.getgroup("OEP", "OEP reporting", "general")
    group.addoption(
        "--org", action="append", default=[],
        help="list of orgs to run tests on"
    )
    group.addoption(
        "--repo", action="append", default=[],
        help="list of specific repositories (specified as org/repo) "
             "to run tests on"
    )
    group.addoption(
        "--username", action="store", default=None,
        help="username to log into github with"
    )
    group.addoption(
        "--password", action="store", default=None,
        help="password to log into github with"
    )
    group.addoption(
        "--token", action="store", default=None,
        help="personal access token to long into github with"
    )

    group.addoption(
        "--oep", action="append", default=[3, 4, 5],
        help="List of OEPs to check for explicit specification of compliance"
    )


def pytest_generate_tests(metafunc):
    """
    Generate test instances for all repositories to be checked.
    """
    hub = login_github(
        metafunc.config.option.username,
        metafunc.config.option.password,
        metafunc.config.option.token,
    )

    if 'github_repo' in metafunc.fixturenames:
        if not metafunc.config.option.org and not metafunc.config.option.repo:
            metafunc.parametrize(
                "github_repo",
                [None],
                scope="session",
            )

            metafunc.parametrize(
                "local_repo",
                ['.'],
                scope="session",
            )
        else:
            repos = []
            if metafunc.config.option.repo:
                repos = [
                    hub.repository(*repo.split('/'))
                    for repo in metafunc.config.option.repo
                ]
            elif metafunc.config.option.org:
                repos = [
                    repo
                    for org in metafunc.config.option.org
                    for repo in hub.organization(org).iter_repos()
                ]
                repos = [repo for repo in repos if not repo.fork]

            metafunc.parametrize(
                "github_repo",
                repos,
                ids=[repo.full_name for repo in repos],
                scope="session",
            )

            metafunc.parametrize(
                "local_repo",
                [None],
                scope="session",
            )

    if 'oep' in metafunc.fixturenames:
        metafunc.parametrize(
            "oep",
            metafunc.config.option.oep
        )


@pytest.fixture(scope="session")
def openedx_yaml(github_repo, local_repo):
    """
    py.test fixture to read the openedx.yaml file from the supplied github_repo.

    Arguments:
        github_repo (:class:`~github3.GitHub`): The repo to read from

    Returns:
        A dictionary with the parsed contents of openedx.yaml.
    """
    if local_repo is not None:
        try:
            with open(os.path.join(local_repo, "openedx.yaml")) as openedx_yaml_file:
                return yaml.safe_load(openedx_yaml_file)
        except IOError:
            return None
    elif github_repo is not None:
        raw_contents = github_repo.contents('openedx.yaml')
        if raw_contents is None:
            return None
        else:
            yaml_contents = yaml.safe_load(raw_contents.decoded)
            return yaml_contents
    else:
        return None
