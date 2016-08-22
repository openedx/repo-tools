"""
py.test plugin to support ``oep2 report``. Adds arguments to py.test,
and creates fixtures for loading git repos.
"""

import os.path
from git.repo.base import Repo, Head
from git.refs.remote import RemoteReference
import pytest
import yaml

from edx_repo_tools.auth import login_github


SYNCED = set()


class Oep2ReportPlugin(object):
    """
    A py.test plugin that wires together the fixtures needed to run the reports.
    """

    def __init__(self, hub):
        self.hub = hub
        self.config = None
        self._repos = None

    def pytest_configure(self, config):
        self.config = config

    def pytest_addoption(self, parser):
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

    @pytest.fixture()
    def git_repo(self, request, github_repo, branch=None, remote='origin', checkout_root=None):
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
        remote_branch = RemoteReference(repo, 'refs/remotes/{}/{}'.format(remote, branch))
        local_branch = Head(repo, 'refs/heads/{}'.format(branch))

        try:
            if head.commit != remote_branch.commit:
                local_branch.commit = remote_branch.commit
                local_branch.checkout()

        except ValueError:
            pytest.xfail("Branch {} is empty".format(branch))

        return repo

    @pytest.fixture()
    def openedx_yaml(self, git_repo):  # pylint: disable=redefined-outer-name
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
