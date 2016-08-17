"""
``oep2 report``: Check repositories for OEP-2 compliance.
"""

import logging
import os.path
import pkg_resources

import click
from git.repo.base import Repo
from git.refs.remote import RemoteReference
from git.cmd import Git
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
@click.option(
    '--trace/--no-trace', default=False,
    help="Trace git and github interactions during reporting",
)

# N.B. We don't use @pass_github here because there isn't a nice way to pass
# the resulting `hub` object into the pytest tests.
@click.option(
    "--checkout-root",
    default=".oep2-workspace",
    help="Where to check out repos that are being checked for oep2 compliance",
)
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

    group.addoption(
        "--checkout-root", action="store", default=".oep2-workspace",
        help="Where to check out repos that are being checked for oep2 compliance",
    )


def pytest_configure(config):
    # Load the Oep2ReportPlugin into pytest. We use a separate object so that we
    # have a place to stash intermediate data (like the list of repos that we're
    # going to test).
    config.pluginmanager.register(Oep2ReportPlugin(config))


class Oep2ReportPlugin(object):
    """
    A py.test plugin that wires together the fixtures needed to run the reports.
    """

    def __init__(self, config):
        self.config = config
        self._repos = None

    def get_repos(self):
        """
        Log in to GitHub and retrieve all of the repos specified on the commandline.
        """

        # N.B. This is a separate function because pytest_generate_tests is called
        # for every check_* function found by py.test, and we don't want to
        # ping github for every checker to find out the list of repos that we're
        # going to test.

        # It's separate from __init__ because we don't want to attempt to login
        # whenever this plugin is loaded, just when it's asked to get a list of
        # repos to pass to a checker function.

        if self._repos is not None:
            return self._repos

        capman = self.config.pluginmanager.getplugin('capturemanager')

        capman.suspendcapture(in_=True)
        self.hub = login_github(
            self.config.option.username,
            self.config.option.password,
            self.config.option.token,
        )
        capman.resumecapture()

        if self.config.option.repo:
            self._repos = [
                self.hub.repository(*repo.split('/'))
                for repo in self.config.option.repo
            ]
        elif self.config.option.org:
            self._repos = [
                repo
                for org in self.config.option.org
                for repo in self.hub.organization(org).iter_repos()
                if not repo.fork
            ]

        return self._repos

    def pytest_generate_tests(self, metafunc):
        """
        Generate test instances for all repositories to be checked.
        """
        if 'github_repo' in metafunc.fixturenames:
            if not metafunc.config.option.org and not metafunc.config.option.repo:
                metafunc.parametrize(
                    "git_repo",
                    [Repo('.')],
                )

                metafunc.parametrize(
                    "github_repo",
                    [None],
                )
            else:
                metafunc.parametrize(
                    "github_repo",
                    self.get_repos(),
                    ids=[repo.full_name for repo in self.get_repos()],
                )

        if 'oep' in metafunc.fixturenames:
            metafunc.parametrize(
                "oep",
                metafunc.config.option.oep,
                ids=["OEP-{}".format(oep) for oep in metafunc.config.option.oep],
            )


SYNCED = set()


@pytest.fixture()
def git_repo(request, github_repo, branch=None, remote='origin', checkout_root=None):
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
        checkout_root = request.config.option.checkout_root

    if not os.path.exists(checkout_root):
        os.makedirs(checkout_root)

    repo_dir = os.path.join(
        os.path.join(checkout_root, github_repo.owner.name),
        github_repo.name
    )

    if github_repo.private:
        repo_url = github_repo.ssh_url
    else:
        repo_url = github_repo.clone_url

    if not os.path.exists(repo_dir):
        repo = Repo.clone_from(repo_url, repo_dir)
    else:
        repo = Repo(repo_dir)

    if github_repo not in SYNCED:

        try:
            remote_obj = repo.remote(remote)
        except ValueError:
            repo.create_remote(remote, repo_url)
            remote_obj = repo.remote(remote)

        if remote_obj.fetch != repo_url:
            remote_obj.set_url(repo_url)

        remote_obj.fetch()
        SYNCED.add(github_repo)

    if branch is None:
        branch = github_repo.default_branch

    head = repo.head
    target = RemoteReference(repo, 'refs/remotes/{}/{}'.format(remote, branch))

    try:
        if head.commit != target.commit:
            target.checkout()
    except ValueError:
        pytest.xfail("Branch {} is empty".format(branch))

    return repo


@pytest.fixture()
def openedx_yaml(git_repo):  # pylint: disable=redefined-outer-name
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
