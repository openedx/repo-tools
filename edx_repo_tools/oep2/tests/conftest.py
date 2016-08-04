import pytest
import yaml
from edx_repo_tools.auth import login_github


def pytest_addoption(parser):
    group = parser.getgroup("OEP", "OEP reporting", "general")
    group.addoption(
        "--org", action="append", default=[],
        help="list of orgs to run tests on"
    )
    group.addoption(
        "--repo", action="append", default=[],
        help="list of specific repositories (specified as org/repo) to run tests on"
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
    hub = login_github(
        metafunc.config.option.username,
        metafunc.config.option.password,
        metafunc.config.option.token,
    )

    if 'github_repo' in metafunc.fixturenames:
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


@pytest.fixture(scope="session")
def openedx_yaml(github_repo):
    raw_contents = github_repo.contents('openedx.yaml')
    if raw_contents is None:
        return None
    else:
        yaml_contents = yaml.safe_load(raw_contents.decoded)
        return yaml_contents
