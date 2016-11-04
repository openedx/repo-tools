from collections import OrderedDict
import json
import textwrap

from github3.repos.repo import Repository
from github3 import GitHubError, GitHub
from mock import Mock
import pytest
import requests

from edx_repo_tools.release.tag_release import (
    openedx_release_repos, get_ref_for_repos, commit_ref_info,
    create_ref_for_repos, remove_ref_for_repos, override_repo_refs
)

expected_repos = {
    'edx/edx-platform': {
        'openedx-release': {
            'ref': 'release',
        }
    },
    'edx/configuration': {
        'openedx-release': {
            'ref': 'master',
        }
    },
    'edx/XBlock': {
        'openedx-release': {
            'parent-repo': 'edx/edx-platform',
        }
    },
}

expected_commits = {
    'edx/edx-platform': {
        'committer': {'name': 'Dev 1'},
        'author': {'name': 'Dev 1'},
        'sha': 'deadbeef12345',
        'ref_type': 'branch',
        'ref': 'release',
        'message': 'commit message for edx-platform release commit',
    },
    'edx/configuration': {
        'committer': {'name': 'Dev 2'},
        'author': {'name': 'Dev 2'},
        'sha': '12345deadbeef',
        'ref_type': 'branch',
        'ref': 'master',
        'message': 'commit message for configuration master commit',
    },
    'edx/XBlock': {
        'committer': {'name': 'Dev 1'},
        'author': {'name': 'Dev 1'},
        'sha': '1a2b3c4d5e6f',
        'ref_type': 'tag',
        'ref': '0.4.4',
        'message': 'commit message for refs/tags/0.4.4',
    }
}

ALREADY_EXISTS = GitHubError(Mock(status_code=422, json=Mock(return_value={"message": "Reference already exists"})))


def mock_repository(name):
    return Mock(spec=Repository, name=name, full_name=name)


def test_get_ref_for_repos():
    repos = [
        mock_repository('edx/edx-platform'),
        mock_repository('edx/configuration'),
        mock_repository('edx/XBlock'),
    ]
    repos[1].ref.return_value = None
    repos[2].ref.return_value = None

    result = get_ref_for_repos(repos, "tag-exists-some-repos")
    expected_result = {
        'edx/edx-platform': {
            'author': repos[0].commit.return_value.commit.author,
            'committer': repos[0].commit.return_value.commit.committer,
            'message': repos[0].commit.return_value.commit.message,
            'ref': 'refs/tags/tag-exists-some-repos',
            'ref_type': repos[0].ref.return_value.type,
            'sha': repos[0].commit.return_value.commit.sha,
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


def test_commit_ref_info():
    repo_objs = {
        repo_name: mock_repository(repo_name)
        for repo_name in expected_repos
    }

    repos = {
        repo_objs[repo_name]: repo_info
        for repo_name, repo_info
        in expected_repos.items()
    }


    mock_hub = Mock(spec=GitHub, repository=lambda org, repo: repo_objs.get("{}/{}".format(org, repo)))

    result = commit_ref_info(repos, mock_hub)

    repo_objs['edx/edx-platform'].branch.assert_called_once_with('release')
    assert not repo_objs['edx/edx-platform'].ref.called
    repo_objs['edx/configuration'].branch.assert_called_once_with('master')
    assert not repo_objs['edx/configuration'].ref.called

    # The XBlock repo shouldn't have been examined at all.
    assert not repo_objs['edx/XBlock'].branch.called

    expected_commits = {
        repo_objs['edx/edx-platform']: {
            'committer': repo_objs['edx/edx-platform'].branch.return_value.commit.commit.committer,
            'author': repo_objs['edx/edx-platform'].branch.return_value.commit.commit.author,
            'sha': repo_objs['edx/edx-platform'].branch.return_value.commit.sha,
            'ref_type': 'branch',
            'ref': 'release',
            'message': repo_objs['edx/edx-platform'].branch.return_value.commit.commit.message,
        },
        repo_objs['edx/configuration']: {
            'committer': repo_objs['edx/configuration'].branch.return_value.commit.commit.committer,
            'author': repo_objs['edx/configuration'].branch.return_value.commit.commit.author,
            'sha': repo_objs['edx/configuration'].branch.return_value.commit.sha,
            'ref_type': 'branch',
            'ref': 'master',
            'message': repo_objs['edx/configuration'].branch.return_value.commit.commit.message,
        },
    }

    assert result == expected_commits


def test_overrides_none():
    result = override_repo_refs(expected_repos)
    assert result == expected_repos


def test_overrides_global_ref():
    result = override_repo_refs(expected_repos, override_ref="abcdef")
    assert result["edx/edx-platform"]["openedx-release"]["ref"] == "abcdef"
    assert result["edx/configuration"]["openedx-release"]["ref"] == "abcdef"


def test_overrides_dict():
    overrides = {
        "edx/edx-platform": "xyz",
        "edx/configuration": "refs/branch/no-way",
        "edx/does-not-exist": "does-not-matter",
    }
    result = override_repo_refs(expected_repos, overrides=overrides)
    assert result["edx/edx-platform"]["openedx-release"]["ref"] == "xyz"
    assert result["edx/configuration"]["openedx-release"]["ref"] == "refs/branch/no-way"


def test_overrides_global_ref_and_dict():
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
    assert result["edx/edx-platform"]["openedx-release"]["ref"] == "xyz"
    assert result["edx/configuration"]["openedx-release"]["ref"] == "fakie-mcfakerson"


def test_create_happy_path():
    repo_objs = {
        repo_name: mock_repository(repo_name)
        for repo_name in expected_commits
    }

    # creating a tag that does not already exist anywhere
    result = create_ref_for_repos(
        {
            repo_objs[repo_name]: ref_info
            for repo_name, ref_info
            in expected_commits.items()
        },
        "tag-exists-no-repos",
        dry=False,
    )
    assert result is True

    repo_objs['edx/edx-platform'].create_ref.assert_called_once_with(
        sha="deadbeef12345",
        ref="refs/tags/tag-exists-no-repos",
    )

    repo_objs['edx/configuration'].create_ref.assert_called_once_with(
        sha="12345deadbeef",
        ref="refs/tags/tag-exists-no-repos",
    )

    repo_objs['edx/XBlock'].create_ref.assert_called_once_with(
        sha="1a2b3c4d5e6f",
        ref="refs/tags/tag-exists-no-repos",
    )


def test_create_existing_tag():

    repo_objs = {
        repo_name: mock_repository(repo_name)
        for repo_name in expected_commits
    }

    repo_objs['edx/edx-platform'].create_ref.side_effect = ALREADY_EXISTS

    # creating a tag that already exists in edx-platform: we'll make sure
    # that edx-platform is attempted *first*
    ordered_commits = OrderedDict(
        (repo_objs[repo_name], expected_commits[repo_name])
        for repo_name
        in ('edx/edx-platform', 'edx/configuration')
    )

    # creating a tag that does not already exist anywhere
    result = create_ref_for_repos(
        ordered_commits,
        "tag-exists-some-repos",
        dry=False,
    )

    assert result is False
    repo_objs['edx/edx-platform'].create_ref.assert_called_once_with(
        sha="deadbeef12345",
        ref="refs/tags/tag-exists-some-repos",
    )

    assert not repo_objs['edx/configuration'].create_ref.called


def test_create_existing_tag_at_end():

    repo_objs = {
        repo_name: mock_repository(repo_name)
        for repo_name in expected_commits
    }

    repo_objs['edx/edx-platform'].create_ref.side_effect = ALREADY_EXISTS

    # creating a tag that already exists in edx-platform: we'll make sure
    # that edx-platform is attempted *last*
    ordered_commits = OrderedDict(
        (repo_objs[repo_name], expected_commits[repo_name])
        for repo_name
        in ('edx/configuration', 'edx/edx-platform')
    )

    result = create_ref_for_repos(
        ordered_commits,
        "tag-exists-some-repos",
        dry=False,
    )
    assert result is False

    repo_objs['edx/edx-platform'].create_ref.assert_called_once_with(
        sha="deadbeef12345",
        ref="refs/tags/tag-exists-some-repos",
    )

    repo_objs['edx/configuration'].create_ref.assert_called_once_with(
        sha="12345deadbeef",
        ref="refs/tags/tag-exists-some-repos",
    )

    # second request failed, so rollback the first.
    repo_objs['edx/configuration'].create_ref.return_value.delete.assert_called_once_with()


def test_create_existing_tag_at_end_no_rollback():

    repo_objs = {
        repo_name: mock_repository(repo_name)
        for repo_name in expected_commits
    }

    repo_objs['edx/edx-platform'].create_ref.side_effect = ALREADY_EXISTS

    # creating a tag that already exists in edx-platform: we'll make sure
    # that edx-platform is attempted *last*
    ordered_commits = OrderedDict(
        (repo_objs[repo_name], expected_commits[repo_name])
        for repo_name
        in ('edx/configuration', 'edx/edx-platform')
    )

    with pytest.raises(RuntimeError) as excinfo:
        result = create_ref_for_repos(
            ordered_commits,
            "tag-exists-some-repos",
            rollback_on_fail=False,
            dry=False,
        )

    repo_objs['edx/edx-platform'].create_ref.assert_called_once_with(
        sha="deadbeef12345",
        ref="refs/tags/tag-exists-some-repos",
    )

    repo_objs['edx/configuration'].create_ref.assert_called_once_with(
        sha="12345deadbeef",
        ref="refs/tags/tag-exists-some-repos",
    )

    # second request failed, no rollback of the first.
    assert not repo_objs['edx/configuration'].create_ref.return_value.delete.called

    assert "No rollback attempted" in str(excinfo.value)
    assert "Reference already exists" in str(excinfo.value)
    assert "Refs exist on the following repos: " in str(excinfo.value)
    assert "edx/configuration" in str(excinfo.value)


def test_create_existing_tag_at_end_rollback_failure():

    repo_objs = {
        repo_name: mock_repository(repo_name)
        for repo_name in expected_commits
    }

    repo_objs['edx/edx-platform'].create_ref.side_effect = ALREADY_EXISTS
    # when we try to delete the configuration tag, it will fail with a 500 error
    repo_objs['edx/configuration'].create_ref.return_value.delete.side_effect = GitHubError(Mock(status_code=500))

    # creating a tag that already exists in edx-platform: we'll make sure
    # that edx-platform is attempted *last*
    ordered_commits = OrderedDict(
        (repo_objs[repo_name], expected_commits[repo_name])
        for repo_name
        in ('edx/configuration', 'edx/edx-platform')
    )

    with pytest.raises(RuntimeError) as excinfo:
        result = create_ref_for_repos(
            ordered_commits,
            "tag-exists-some-repos",
            dry=False,
        )

    repo_objs['edx/edx-platform'].create_ref.assert_called_once_with(
        sha="deadbeef12345",
        ref="refs/tags/tag-exists-some-repos",
    )

    repo_objs['edx/configuration'].create_ref.assert_called_once_with(
        sha="12345deadbeef",
        ref="refs/tags/tag-exists-some-repos",
    )

    # second response failed, so try to rollback. 
    # ... but configuration fails, so we get an exception
    repo_objs['edx/configuration'].create_ref.return_value.delete.assert_called_once_with()
    assert "failed to delete ref on the following repos: edx/configuration" in str(excinfo)


def test_remove_all():
    repos = [
        mock_repository('edx/edx-platform'),
        mock_repository('edx/configuration'),
    ]
    result = remove_ref_for_repos(repos, "tag-exists-all-repos", dry=False)
    assert result is True
    for repo in repos:
        repo.ref.assert_called_once_with('tags/tag-exists-all-repos')
        ref = repo.ref.return_value
        ref.delete.assert_called_once_with()


def test_remove_some():
    repos = [
        mock_repository('edx/edx-platform'),
        mock_repository('edx/configuration'),
    ]
    repos[0].ref.return_value = None

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

    with pytest.raises(RuntimeError) as excinfo:
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
    result = remove_ref_for_repos(repos, "{}tag-exists-all-repos".format(ref_prefix), use_tag=use_tag, dry=False)
    assert result is True
    for repo in repos:
        repo.ref.assert_called_once_with('{}tag-exists-all-repos'.format(call_prefix))
        ref = repo.ref.return_value
        ref.delete.assert_called_once_with()
