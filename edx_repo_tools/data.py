import logging

from github3.exceptions import NotFoundError
import yaml


logging.basicConfig()
LOGGER = logging.getLogger(__name__)
OPEN_EDX_YAML = 'openedx.yaml'
CATALOG_INFO_YAML = 'catalog-info.yaml'


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


def find_file_content(repo, branch):
    """
    Finds the data from all catalog-info.yaml or openedx.yaml files found in repositories in ``repo``
    on any of ``branches``.
    First, we check for catalog-info.yaml, If catalog-info.yaml is not found, we look for openedx.yaml file.

    """

    file_names = [CATALOG_INFO_YAML, OPEN_EDX_YAML]    
    contents = None
    for file_name in file_names:
        try:
            contents = repo.file_contents(file_name, ref=branch)
            break
        except NotFoundError:
            contents = None
            pass

    return contents   


def iter_openedx_release_yaml(hub, orgs, branches=None):
    """
    Yield the data from all catalog-info.yaml or openedx.yaml files found in repositories in ``orgs``
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
            contents = find_file_content(repo, branch)

            if contents is not None:
                LOGGER.debug("Found %s at %s:%s", contents, repo.full_name, branch)
                try:
                    data = yaml.safe_load(contents.decoded)
                except Exception as exc:
                    LOGGER.error("Couldn't parse %s from %s:%s, skipping repo", contents, repo.full_name, branch, exc_info=True)
                else:
                    if data is not None:
                        yield repo, data

                break
