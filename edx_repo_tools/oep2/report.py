"""
``oep2 report``: Check repositories for OEP-2 compliance.
"""

import logging
import os.path
import pkg_resources
import tempfile

import click
from git.repo.base import Repo
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
                "git_repo",
                [Repo('.')],
                scope="session",
            )

            metafunc.parametrize(
                "github_repo",
                [None],
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

    if 'oep' in metafunc.fixturenames:
        metafunc.parametrize(
            "oep",
            metafunc.config.option.oep
        )


@pytest.fixture(scope="session")
def git_repo(github_repo, branch="master", checkout_root=None):
    """
    py.test fixture to clone a GitHub based repo onto the local disk.

    Arguments:
        github_repo (:class:`~github3.GitHub`): The repo to read from
        branch (str): The branch to check out

    Returns:
        A :class:`~git.repo.base.Repo` object, with the master branch checked out
        and up to date with the remote.
    """
    if checkout_root is None:
        checkout_root = os.path.join(tempfile.gettempdir(), '.oep2-workspace')

    if not os.path.exists(checkout_root):
        os.makedirs(checkout_root)

    repo_dir = os.path.join(
        os.path.join(checkout_root, github_repo.owner.name),
        github_repo.name
    )

    if not os.path.exists(repo_dir):
        repo = Repo.clone_from(github_repo.git_url, repo_dir)
    else:
        repo = Repo(repo_dir)

    if repo.is_dirty():
        raise Exception("Can't update a dirty repository from github")
   
    try:
        origin = repo.remote('origin')
    except ValueError:
        repo.create_remote('origin', github_repo.git_url)
        origin = repo.remote('origin')

    if origin.fetch != github_repo.git_url:
        origin.set_url(github_repo.git_url)

    origin.fetch()

    head = repo.create_head(
        'refs/heads/{}'.format(branch),
        '{}/{}'.format(origin.name, branch)
    )

    head.checkout(force=True)

    return repo



@pytest.fixture(scope="session")
def openedx_yaml(git_repo):
    """
    py.test fixture to read the openedx.yaml file from the supplied github_repo.

    Arguments:
        github_repo (:class:`~github3.GitHub`): The repo to read from

    Returns:
        A dictionary with the parsed contents of openedx.yaml.
    """
    try:
        with open(os.path.join(git_repo.working_tree_dir, "openedx.yaml")) as openedx_yaml_file:
            return yaml.safe_load(openedx_yaml_file)
    except IOError:
        return None
