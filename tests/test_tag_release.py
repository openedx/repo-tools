"""Tests of tag_release.py"""

from collections import OrderedDict

from github3 import GitHubError
from github3.exceptions import NotFoundError
from github3.repos.repo import Repository
from unittest.mock import Mock
import pytest

from edx_repo_tools.release.tag_release import (
    get_ref_for_repos, commit_ref_info,
    create_ref_for_repos, remove_ref_for_repos, override_repo_refs,
    TagReleaseError
)

ALREADY_EXISTS = GitHubError(Mock(status_code=422, json=Mock(return_value={"message": "Reference already exists"})))


class FakeNotFoundError(NotFoundError):
    """A NotFoundError with enough content to please the code."""
    status_code = 404
    content = "A fake response"

    def __init__(self):
        super().__init__(self)


def mock_repository(name, has_refs=False):
    """Make a mock Repository object.

    Arguments:
        name (str): will be the name and full_name of the repo.
        has_refs (bool): if False, has no refs. If True, returns mock refs.

    Returns:
        A Mock

    """
    repo = Mock(spec=Repository, name=name, full_name=name)
    if not has_refs:
        repo.ref.side_effect = FakeNotFoundError
    return repo

def find_repo_item(repos, name):
    """Find a repo in a dict mapping Repository objects to data.

    Arguments:
        repos: (dict mapping Repository objects to data)
        name: (str) the full_name of the repo to find.

    Returns:
        The data found in the dict, or None if not found.

    """
    for repo, data in repos.items():
        if repo.full_name == name:
            return repo, data
    return None, None


def find_repo(repos, name):
    """Find the key in `repos` that is Repository(`name`)"""
    return find_repo_item(repos, name)[0]


def find_repo_data(repos, name):
    """Find the value in `repos` associated with Repository(`name`)"""
    return find_repo_item(repos, name)[1]


@pytest.fixture
def expected_repos():
    """Newly created test data for each test.

    The keys are mocks, so are changed by each test, so we need new data for
    each test, not a global constant.

    """
    repos = {
        mock_repository('edx/edx-platform'): {
            'openedx-release': {
                'ref': 'release',
            }
        },
        mock_repository('edx/configuration'): {
            'openedx-release': {
                'ref': 'master',
            }
        },
        mock_repository('edx/XBlock'): {
            'openedx-release': {
                'parent-repo': 'edx/edx-platform',
            }
        },
    }
    return repos


@pytest.fixture
def expected_commits():
    """Newly created test data for each test.

    The keys are mocks, so are changed by each test, so we need new data for
    each test, not a global constant.

    """
    commits = {
        mock_repository('edx/edx-platform'): {
            'committer': {'name': 'Dev 1'},
            'author': {'name': 'Dev 1'},
            'sha': 'deadbeef12345',
            'ref_type': 'branch',
            'ref': 'release',
            'message': 'commit message for edx-platform release commit',
        },
        mock_repository('edx/configuration'): {
            'committer': {'name': 'Dev 2'},
            'author': {'name': 'Dev 2'},
            'sha': '12345deadbeef',
            'ref_type': 'branch',
            'ref': 'master',
            'message': 'commit message for configuration master commit',
        },
        mock_repository('edx/XBlock'): {
            'committer': {'name': 'Dev 1'},
            'author': {'name': 'Dev 1'},
            'sha': '1a2b3c4d5e6f',
            'ref_type': 'tag',
            'ref': '0.4.4',
            'message': 'commit message for refs/tags/0.4.4',
        }
    }
    return commits


def test_get_ref_for_repos():
    repos = [
        mock_repository('edx/edx-platform', has_refs=True),
        mock_repository('edx/configuration'),
        mock_repository('edx/XBlock'),
    ]

    result = get_ref_for_repos(repos, "tag-exists-some-repos")
    expected_result = {
        'edx/edx-platform': {
            'author': repos[0].git_commit().refresh.return_value.author,
            'committer': repos[0].git_commit().refresh.return_value.committer,
            'message': repos[0].git_commit().refresh.return_value.message,
            'ref': 'refs/tags/tag-exists-some-repos',
            'ref_type': 'tag',
            'sha': repos[0].git_commit().refresh.return_value.sha,
        }
    }
    assert result == expected_result


def test_get_ref_for_repos_not_exist():
    repos = [
        mock_repository('edx/edx-platform'),
        mock_repository('edx/configuration'),
        mock_repository('edx/XBlock'),
    ]
    for repo in repos:
        repo.ref.return_value = None
    result = get_ref_for_repos(repos, "tag-exists-no-repos")
    assert result == {}


def test_commit_ref_info(expected_repos):
    result = commit_ref_info(expected_repos)

    edx_edx_platform = find_repo(expected_repos, 'edx/edx-platform')
    edx_configuration = find_repo(expected_repos, 'edx/configuration')
    edx_edx_platform.branch.assert_called_once_with('release')
    assert not edx_edx_platform.ref.called
    edx_configuration.branch.assert_called_once_with('master')
    assert not edx_configuration.ref.called

    # The XBlock repo shouldn't have been examined at all.
    assert not find_repo(expected_repos, 'edx/XBlock').branch.called

    edx_platform_commit = edx_edx_platform.git_commit().refresh()
    configuration_commit = edx_configuration.git_commit().refresh()

    expected_commits = {
        edx_edx_platform: {
            'committer': edx_platform_commit.committer,
            'author': edx_platform_commit.author,
            'sha': edx_platform_commit.sha,
            'ref_type': 'branch',
            'ref': 'release',
            'message': edx_platform_commit.message,
        },
        edx_configuration: {
            'committer': configuration_commit.committer,
            'author': configuration_commit.author,
            'sha': configuration_commit.sha,
            'ref_type': 'branch',
            'ref': 'master',
            'message': configuration_commit.message,
        },
    }

    assert result == expected_commits


def test_overrides_none(expected_repos):
    result = override_repo_refs(expected_repos)
    assert result == expected_repos


def test_overrides_global_ref(expected_repos):
    result = override_repo_refs(expected_repos, override_ref="abcdef")
    assert find_repo_data(result, "edx/edx-platform")["openedx-release"]["ref"] == "abcdef"
    assert find_repo_data(result, "edx/configuration")["openedx-release"]["ref"] == "abcdef"


def test_overrides_dict(expected_repos):
    overrides = {
        "edx/edx-platform": "xyz",
        "edx/configuration": "refs/branch/no-way",
        "edx/does-not-exist": "does-not-matter",
    }
    result = override_repo_refs(expected_repos, overrides=overrides)
    assert find_repo_data(result, "edx/edx-platform")["openedx-release"]["ref"] == "xyz"
    assert find_repo_data(result, "edx/configuration")["openedx-release"]["ref"] == "refs/branch/no-way"


def test_overrides_global_ref_and_dict(expected_repos):
    override_ref = "fakie-mcfakerson"
    overrides = {
        "edx/edx-platform": "xyz",
        "edx/does-not-exist": "does-not-matter",
    }
    result = override_repo_refs(
        expected_repos,
        override_ref=override_ref,
        overrides=overrides,
    )
    assert find_repo_data(result, "edx/edx-platform")["openedx-release"]["ref"] == "xyz"
    assert find_repo_data(result, "edx/configuration")["openedx-release"]["ref"] == "fakie-mcfakerson"


def test_create_happy_path(expected_commits):
    # Creating a tag that does not already exist anywhere.
    result = create_ref_for_repos(
        expected_commits,
        "tag-exists-no-repos",
        dry=False
    )
    assert result is True

    find_repo(expected_commits, 'edx/edx-platform').create_ref.assert_called_once_with(
        sha="deadbeef12345",
        ref="refs/tags/tag-exists-no-repos",
    )

    find_repo(expected_commits, 'edx/configuration').create_ref.assert_called_once_with(
        sha="12345deadbeef",
        ref="refs/tags/tag-exists-no-repos",
    )

    find_repo(expected_commits, 'edx/XBlock').create_ref.assert_called_once_with(
        sha="1a2b3c4d5e6f",
        ref="refs/tags/tag-exists-no-repos",
    )


def test_create_existing_tag(expected_commits):
    # Creating a tag that already exists in edx-platform: we'll make sure
    # that edx-platform is attempted *first*, so that the function will
    # return before touching edx/configuration.
    ordered_commits = OrderedDict([
        find_repo_item(expected_commits, 'edx/edx-platform'),
        find_repo_item(expected_commits, 'edx/configuration'),
    ])

    find_repo(ordered_commits, 'edx/edx-platform').create_ref.side_effect = ALREADY_EXISTS

    # Creating a tag that does not already exist anywhere.
    result = create_ref_for_repos(
        ordered_commits,
        "tag-exists-some-repos",
        dry=False,
    )

    assert result is False
    find_repo(ordered_commits, 'edx/edx-platform').create_ref.assert_called_once_with(
        sha="deadbeef12345",
        ref="refs/tags/tag-exists-some-repos",
    )

    assert not find_repo(ordered_commits, 'edx/configuration').create_ref.called


def test_create_existing_tag_at_end(expected_commits):
    # Creating a tag that already exists in edx-platform: we'll make sure
    # that edx-platform is attempted *last* so that other repos will have
    # been touched first.
    ordered_commits = OrderedDict([
        find_repo_item(expected_commits, 'edx/configuration'),
        find_repo_item(expected_commits, 'edx/edx-platform'),
    ])

    find_repo(ordered_commits, 'edx/edx-platform').create_ref.side_effect = ALREADY_EXISTS

    result = create_ref_for_repos(
        ordered_commits,
        "tag-exists-some-repos",
        dry=False,
    )
    assert result is False

    find_repo(ordered_commits, 'edx/edx-platform').create_ref.assert_called_once_with(
        sha="deadbeef12345",
        ref="refs/tags/tag-exists-some-repos",
    )

    find_repo(ordered_commits, 'edx/configuration').create_ref.assert_called_once_with(
        sha="12345deadbeef",
        ref="refs/tags/tag-exists-some-repos",
    )

    # Second request failed, so rollback the first.
    find_repo(ordered_commits, 'edx/configuration').create_ref.return_value.delete.assert_called_once_with()


def test_create_existing_tag_at_end_no_rollback(expected_commits):
    # Creating a tag that already exists in edx-platform: we'll make sure
    # that edx-platform is attempted *last* so that other repos will have
    # been touched first.
    ordered_commits = OrderedDict([
        find_repo_item(expected_commits, 'edx/configuration'),
        find_repo_item(expected_commits, 'edx/edx-platform'),
    ])

    find_repo(ordered_commits, 'edx/edx-platform').create_ref.side_effect = ALREADY_EXISTS

    with pytest.raises(TagReleaseError) as excinfo:
        create_ref_for_repos(
            ordered_commits,
            "tag-exists-some-repos",
            rollback_on_fail=False,
            dry=False,
        )

    find_repo(ordered_commits, 'edx/edx-platform').create_ref.assert_called_once_with(
        sha="deadbeef12345",
        ref="refs/tags/tag-exists-some-repos",
    )

    find_repo(ordered_commits, 'edx/configuration').create_ref.assert_called_once_with(
        sha="12345deadbeef",
        ref="refs/tags/tag-exists-some-repos",
    )

    # Second request failed, no rollback of the first.
    assert not find_repo(ordered_commits, 'edx/configuration').create_ref.return_value.delete.called

    assert "No rollback attempted" in str(excinfo.value)
    assert "Reference already exists" in str(excinfo.value)
    assert "Refs exist on the following repos: " in str(excinfo.value)
    assert "edx/configuration" in str(excinfo.value)


def test_create_existing_tag_at_end_rollback_failure(expected_commits):
    # Creating a tag that already exists in edx-platform: we'll make sure
    # that edx-platform is attempted *last* so that other repos will have
    # been touched first.
    ordered_commits = OrderedDict([
        find_repo_item(expected_commits, 'edx/configuration'),
        find_repo_item(expected_commits, 'edx/edx-platform'),
    ])

    edx_edx_platform = find_repo(ordered_commits, 'edx/edx-platform')
    edx_edx_platform.create_ref.side_effect = ALREADY_EXISTS
    # When we try to delete the configuration tag, it will fail with a 500 error
    edx_configuration = find_repo(ordered_commits, 'edx/configuration')
    edx_configuration.create_ref.return_value.delete.side_effect = GitHubError(Mock(status_code=500))

    with pytest.raises(TagReleaseError) as excinfo:
        create_ref_for_repos(
            ordered_commits,
            "tag-exists-some-repos",
            dry=False,
        )

    edx_edx_platform.create_ref.assert_called_once_with(
        sha="deadbeef12345",
        ref="refs/tags/tag-exists-some-repos",
    )

    edx_configuration.create_ref.assert_called_once_with(
        sha="12345deadbeef",
        ref="refs/tags/tag-exists-some-repos",
    )

    # Second response failed, so try to rollback.
    # ... but configuration fails, so we get an exception
    edx_configuration.create_ref.return_value.delete.assert_called_once_with()
    assert "failed to delete ref on the following repos: edx/configuration" in str(excinfo)


def test_remove_all():
    repos = [
        mock_repository('edx/edx-platform', has_refs=True),
        mock_repository('edx/configuration', has_refs=True),
    ]
    result = remove_ref_for_repos(repos, "tag-exists-all-repos", dry=False)
    assert result is True
    for repo in repos:
        repo.ref.assert_called_once_with('tags/tag-exists-all-repos')
        ref = repo.ref.return_value
        ref.delete.assert_called_once_with()


def test_remove_some():
    repos = [
        mock_repository('edx/edx-platform', has_refs=False),
        mock_repository('edx/configuration', has_refs=True),
    ]

    result = remove_ref_for_repos(repos, "tag-exists-some-repos", dry=False)
    assert result is True
    repos[0].ref.assert_called_once_with('tags/tag-exists-some-repos')
    for repo in repos[1:]:
        repo.ref.assert_called_once_with('tags/tag-exists-some-repos')
        ref = repo.ref.return_value
        ref.delete.assert_called_once_with()


def test_remove_none():
    repos = [
        mock_repository('edx/edx-platform'),
        mock_repository('edx/configuration'),
    ]

    for repo in repos:
        repo.ref.return_value = None

    result = remove_ref_for_repos(repos, "tag-exists-no-repos", dry=False)
    assert result is False

    for repo in repos:
        repo.ref.assert_called_once_with('tags/tag-exists-no-repos')


def test_remove_with_errors():
    repos = [
        Mock(spec=Repository, full_name="edx/edx-platform"),
        Mock(spec=Repository, full_name="edx/configuration"),
    ]

    # when we try to get the edx-platform tag, it will fail with a 500 error
    repos[0].ref.side_effect = GitHubError(Mock(status_code=500))

    with pytest.raises(TagReleaseError) as excinfo:
        remove_ref_for_repos(repos, "tag-exists-all-repos", dry=False)

    for repo in repos:
        repo.ref.assert_called_once_with('tags/tag-exists-all-repos')

    for repo in repos[1:]:
        ref = repo.ref.return_value
        ref.delete.assert_called_once_with()

    assert "Failed to remove the ref from the following repos: edx/edx-platform" in str(excinfo)


@pytest.mark.parametrize("ref_prefix, use_tag, call_prefix", [
    ("", True, "tags/"),
    ("", False, "heads/"),
    ("tags/", True, "tags/"),
    ("tags/", False, "tags/"),
    ("refs/tags/", True, "tags/"),
    ("refs/tags/", False, "tags/"),
    ("heads/", True, "heads/"),
    ("heads/", False, "heads/"),
    ("refs/heads/", True, "heads/"),
    ("refs/heads/", False, "heads/"),
])
def test_remove_ref_formatting(ref_prefix, use_tag, call_prefix):
    repos = [
        Mock(spec=Repository, full_name="edx/edx-platform"),
        Mock(spec=Repository, full_name="edx/configuration"),
    ]
    result = remove_ref_for_repos(repos, f"{ref_prefix}tag-exists-all-repos", use_tag=use_tag, dry=False)
    assert result is True
    for repo in repos:
        repo.ref.assert_called_once_with(f'{call_prefix}tag-exists-all-repos')
        ref = repo.ref.return_value
        ref.delete.assert_called_once_with()
