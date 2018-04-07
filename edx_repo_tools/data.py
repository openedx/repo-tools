from datetime import date
import functools
import itertools
import logging
import os.path

import click
from edx_repo_tools.auth import pass_github
from lazy import lazy
import yaml


logging.basicConfig()
LOGGER = logging.getLogger(__name__)
OPEN_EDX_YAML = 'openedx.yaml'


def iter_nonforks(hub, orgs):
    for org in orgs:
        for repo in hub.organization(org).iter_repos():
            if repo.fork:
                LOGGER.debug("Skipping %s because it is a fork", repo.full_name)
            else:
                yield repo


def iter_openedx_yaml(hub, orgs, branches=None):
    """
    Yield the data from all openedx.yaml files found in repositories in ``orgs``
    on any of ``branches``.

    Arguments:
        hub (GitHub): A connection to GitHub.
        orgs: A list of github orgs to search for openedx.yaml files.
        branches: A list of branches to search for openedx.yaml files. If
            that file exists on multiple branches, then only the contents
            of the first will be yielded. The repository's default branch will
            always be searched (but will be lower priority than any supplied branch).
            (optional)
    """
    if branches is None:
        branches = []

    for repo in iter_nonforks(hub, orgs):
        for branch in itertools.chain(branches, [repo.default_branch]):
            contents = repo.contents(OPEN_EDX_YAML, ref=branch)
            if contents is not None:
                LOGGER.debug("Found openedx.yaml at %s:%s", repo.full_name, branch)
                yield repo, yaml.safe_load(contents.decoded)
                break


class Person(object):
    """
    A wrapper object around data parsed from people.yaml.
    """
    def __init__(self, username, name, email, agreement, email_ok=True,
                 other_emails=None, institution=None, committer=None, jira=None,
                 comments=None, expires_on=None, before=None, beta=None,
                 is_robot=None,
                ):
        self.username = username
        self.name = name
        self.email = email
        self.email_ok = email_ok
        self.other_emails = other_emails
        self.agreement = agreement
        self.institution = institution
        self.committer = committer
        self.jira = jira
        self.comments = comments
        self.expires_on = expires_on
        self.before = before
        self.beta = beta
        self.is_robot = is_robot

    @classmethod
    def from_yaml(cls, username, yaml_data):
        """
        Create a Person object from parsed yaml data.
        """
        return cls(username=username, **yaml_data)

    def associated_with(self, *institutions):
        """
        Return True if this Person is associated with an institution in
        ``institutions``.

        Arguments:
            *institutions: The institutions to check against
        """
        if self.agreement != 'institution':
            return False

        if self.expires_on and self.expires_on < date.today():
            return False

        institutions = [inst.lower() for inst in institutions]

        if self.institution and self.institution.lower() in institutions:
            return True

        return False


class RepoToolsData(object):

    def _read_file(self, filename):
        raise NotImplementedError()

    @lazy
    def labels(self):
        """
        The parsed contents of ``labels.yaml``.
        """
        return self._read_file('labels.yaml')

    @lazy
    def orgs(self):
        """
        The parsed contents of ``orgs.yaml``.
        """
        return self._read_file('orgs.yaml')

    @lazy
    def people(self):
        """
        The parsed contents of ``people.yaml``.
        """
        return {
            username: Person.from_yaml(username, data)
            for username, data
            in self._read_file('people.yaml').items()
        }


class LocalRepoToolsData(RepoToolsData):

    def __init__(self, root):
        self.root = root

    def _read_file(self, filename):
        with open(os.path.join(self.root, filename)) as file_data:
            return yaml.safe_load(file_data)


class RemoteRepoToolsData(RepoToolsData):
    def __init__(self, repo):
        self.repo = repo

    def _read_file(self, filename):
        return yaml.safe_load(self.repo.contents(filename).decoded)


def pass_repo_tools_data(f):
    """
    A click decorator that passes a logged-in GitHub instance to a click
    interface (and exposes the appropriate arguments to configure that
    instance), and also passes a configured RepoToolsData.

    For example:

        @click.command()
        @pass_repo_tools_data
        @click.option(
            '--dry/--yes',
            default=True,
            help='Actually create the pull requests',
        )
        def explode(hub, repo_tools_data, dry):
            print repo_tools_data.labels
    """

    # Mark that pass_repo_tools_data has been applied already to
    # `f`, so that if the decorator is applied multiple times,
    # it won't pass the `hub` argument multiple times, and
    # so that multiple copies of the click arguments won't be added.
    if getattr(f, '_pass_repo_tools_data_applied', False):
        return f
    f._pass_repo_tools_data_applied = True

    # pylint: disable=missing-docstring
    @click.option(
        '--local',
        default='../repo-tools-data',
        help='Specify the path to a local checkout of edx/repo-tools-data to use',
    )
    @click.option(
        '--remote',
        is_flag=True,
        default=False,
        envvar='REPO_TOOLS_LATEST_PEOPLE',
        help="Use data from edx/repo-tools-data, rather than a local checkout",
    )
    @pass_github
    @functools.wraps(f)
    def wrapped(hub, local, remote, *args, **kwargs):

        if remote:
            repo_tools_data = RemoteRepoToolsData(hub.repository('edx', 'repo-tools-data'))
        else:
            repo_tools_data = LocalRepoToolsData(local)

        return f(repo_tools_data=repo_tools_data, hub=hub, *args, **kwargs)
    return wrapped
