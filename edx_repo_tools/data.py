from datetime import date
import functools
import logging
import os.path

import click
from github3.exceptions import NotFoundError
from lazy import lazy
import yaml

from edx_repo_tools.auth import pass_github


logging.basicConfig()
LOGGER = logging.getLogger(__name__)
OPEN_EDX_YAML = 'openedx.yaml'


def iter_nonforks(hub, orgs):
    """Yield all the non-fork repos in a GitHub organization.

    Arguments:
        hub (:class:`~github3.GitHub`): A connection to GitHub.
        orgs (list of str): the GitHub organizations to search.

    Yields:
        Repositories (:class:`~github3.Repository`)

    """
    for org in orgs:
        for repo in hub.organization(org).repositories():
            if repo.fork:
                LOGGER.debug("Skipping %s because it is a fork", repo.full_name)
            else:
                yield repo


def iter_openedx_yaml(hub, orgs, branches=None):
    """
    Yield the data from all openedx.yaml files found in repositories in ``orgs``
    on any of ``branches``.

    Arguments:
        hub (:class:`~github3.GitHub`): A connection to GitHub.
        orgs (list of str): A GitHub organizations to search for openedx.yaml files.
        branches (list of str): Branches to search for openedx.yaml files. If
            that file exists on multiple branches, then only the contents
            of the first will be yielded.  (optional, defaults to the default
            branch in the repo).

    Yields:
        Repositories (:class:`~github3.Repository)

    """
    for repo in iter_nonforks(hub, orgs):
        for branch in (branches or [repo.default_branch]):
            try:
                contents = repo.file_contents(OPEN_EDX_YAML, ref=branch)
            except NotFoundError:
                contents = None

            if contents is not None:
                LOGGER.debug("Found openedx.yaml at %s:%s", repo.full_name, branch)
                try:
                    yield repo, yaml.safe_load(contents.decoded)
                except Exception as exc:
                    LOGGER.error("Couldn't parse openedx.yaml from %s:%s, skipping repo", repo.full_name, branch, exc_info=True)
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
        return yaml.safe_load(self.repo.file_contents(filename).decoded)


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
