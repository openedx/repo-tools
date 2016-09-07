import functools
import logging
import os.path

import click
from edx_repo_tools.auth import pass_github
from lazy import lazy
import yaml


logging.basicConfig()
LOGGER = logging.getLogger(__name__)
OPEN_EDX_YAML = 'openedx.yaml'

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

    for org in orgs:
        for repo in hub.organization(org).iter_repos():
            if repo.fork:
                LOGGER.debug("Skipping %s because it is a fork", repo.full_name)
                continue

            for branch in branches + [repo.default_branch]:
                contents = repo.contents(OPEN_EDX_YAML, ref=branch)
                if contents is not None:
                    LOGGER.debug("Found openedx.yaml at %s:%s", repo.full_name, branch)
                    yield repo.full_name, yaml.safe_load(contents.decoded)
                    break


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
        return self._read_file('people.yaml')


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
    @pass_github
    @functools.wraps(f)
    def wrapped(hub, local, *args, **kwargs):

        if int(os.environ.get('REPO_TOOLS_LATEST_PEOPLE', '0')):
            repo_tools_data = RemoteRepoToolsData(hub.repository('edx', 'repo-tools-data'))
        else:
            repo_tools_data = LocalRepoToolsData(local)

        return f(repo_tools_data=repo_tools_data, hub=hub, *args, **kwargs)
    return wrapped
