from collections import OrderedDict
import json

import pytest
import requests

from edx_repo_tools.release.tag_release import (
    openedx_release_repos, get_ref_for_repos, commit_ref_info,
    create_ref_for_repos, remove_ref_for_repos, override_repo_refs
)

pytestmark = pytest.mark.usefixtures("common_mocks")


expected_repos = {
    'edx/edx-platform': {
        'openedx-release': {
            'ref': 'release',
            'requirements': 'requirements/edx/github.txt',
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


def test_get_repos(session):
    repos = openedx_release_repos(session)
    assert repos == expected_repos


def test_get_ref_for_repos(session):
    result = get_ref_for_repos(expected_repos, "tag-exists-some-repos", session)
    expected_result = {
        'edx/edx-platform': {
            'author': {'name': 'Dev 6'},
            'committer': {'name': 'Dev 6'},
            'message': 'commit message for refs/tags/tag-exists-some-repos',
            'ref': 'refs/tags/tag-exists-some-repos',
            'ref_type': 'tag',
            'sha': '65656565',
        }
    }
    assert result == expected_result


def test_get_ref_for_repos_not_exist(session):
    result = get_ref_for_repos(expected_repos, "tag-exists-no-repos", session)
    assert result == {}


def test_commit_ref_info(session):
    result = commit_ref_info(expected_repos, session)
    assert result == expected_commits


def test_overrides_none():
    result = override_repo_refs(expected_repos)
    assert result == expected_repos


def test_overrides_global_ref():
    result = override_repo_refs(expected_repos, override_ref="abcdef")
    assert result["edx/edx-platform"]["openedx-release"]["ref"] == "abcdef"
    assert result["edx/configuration"]["openedx-release"]["ref"] == "abcdef"
    assert result["edx/XBlock"]["openedx-release"]["ref"] == "abcdef"
    assert "parent-repo" not in result["edx/XBlock"]["openedx-release"]


def test_overrides_dict():
    overrides = {
        "edx/edx-platform": "xyz",
        "edx/configuration": "refs/branch/no-way",
        "edx/does-not-exist": "does-not-matter",
    }
    result = override_repo_refs(expected_repos, overrides=overrides)
    assert result["edx/edx-platform"]["openedx-release"]["ref"] == "xyz"
    assert result["edx/configuration"]["openedx-release"]["ref"] == "refs/branch/no-way"
    assert result["edx/XBlock"]["openedx-release"]["parent-repo"] == "edx/edx-platform"
    assert "ref" not in result["edx/XBlock"]["openedx-release"]


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
    assert result["edx/XBlock"]["openedx-release"]["ref"] == "fakie-mcfakerson"
    assert "parent-repo" not in result["edx/XBlock"]["openedx-release"]


def test_create_happy_path(session, responses):
    # creating a tag that does not already exist anywhere
    result = create_ref_for_repos(
        expected_commits,
        "tag-exists-no-repos",
        session,
    )
    assert result is True
    assert len(responses.calls) == 3
    # calls could be made in any order
    platform_url = "https://api.github.com/repos/edx/edx-platform/git/refs"
    platform_call = [call for call in responses.calls if call.request.url == platform_url][0]
    assert platform_call.request.method == "POST"
    assert json.loads(platform_call.request.body) == {
        "sha": "deadbeef12345",
        "ref": "refs/tags/tag-exists-no-repos",
    }
    configuration_url = "https://api.github.com/repos/edx/configuration/git/refs"
    configuration_call = [call for call in responses.calls if call.request.url == configuration_url][0]
    assert configuration_call.request.method == "POST"
    assert json.loads(configuration_call.request.body) == {
        "sha": "12345deadbeef",
        "ref": "refs/tags/tag-exists-no-repos",
    }
    xblock_url = "https://api.github.com/repos/edx/XBlock/git/refs"
    xblock_call = [call for call in responses.calls if call.request.url == xblock_url][0]
    assert xblock_call.request.method == "POST"
    assert json.loads(xblock_call.request.body) == {
        "sha": "1a2b3c4d5e6f",
        "ref": "refs/tags/tag-exists-no-repos",
    }


def test_create_existing_tag(session, responses):
    # creating a tag that already exists in edx-platform: we'll make sure
    # that edx-platform is attempted *first*
    ordered_commits = OrderedDict(
        sorted(expected_commits.items(), key=lambda x: x[0], reverse=True)
    )
    result = create_ref_for_repos(
        ordered_commits,
        "tag-exists-some-repos",
        session,
    )
    assert result is False
    assert len(responses.calls) == 1
    assert responses.calls[0].request.url == "https://api.github.com/repos/edx/edx-platform/git/refs"
    payload = json.loads(responses.calls[0].request.body)
    assert payload == {
        "sha": "deadbeef12345",
        "ref": "refs/tags/tag-exists-some-repos",
    }

def test_create_existing_tag_at_end(session, responses):
    # creating a tag that already exists in edx-platform: we'll make sure
    # that edx-platform is attempted *last*
    ordered_commits = OrderedDict(
        sorted(expected_commits.items(), key=lambda x: x[0], reverse=False)
    )
    result = create_ref_for_repos(
        ordered_commits,
        "tag-exists-some-repos",
        session,
    )
    assert result is False
    assert len(responses.calls) == 5
    assert responses.calls[0].request.url == "https://api.github.com/repos/edx/XBlock/git/refs"
    xb_payload = json.loads(responses.calls[0].request.body)
    assert xb_payload == {
        "sha": "1a2b3c4d5e6f",
        "ref": "refs/tags/tag-exists-some-repos",
    }
    assert responses.calls[1].request.url == "https://api.github.com/repos/edx/configuration/git/refs"
    conf_payload = json.loads(responses.calls[1].request.body)
    assert conf_payload == {
        "sha": "12345deadbeef",
        "ref": "refs/tags/tag-exists-some-repos",
    }
    assert responses.calls[2].request.url == "https://api.github.com/repos/edx/edx-platform/git/refs"
    plat_payload = json.loads(responses.calls[2].request.body)
    assert plat_payload == {
        "sha": "deadbeef12345",
        "ref": "refs/tags/tag-exists-some-repos",
    }
    # third request failed, so rollback the other two
    assert responses.calls[3].request.url == "https://api.github.com/repos/edx/XBlock/git/refs/tags/tag-exists-some-repos"
    assert responses.calls[3].request.method == 'DELETE'
    assert responses.calls[4].request.url == "https://api.github.com/repos/edx/configuration/git/refs/tags/tag-exists-some-repos"
    assert responses.calls[4].request.method == 'DELETE'


def test_create_existing_tag_at_end_no_rollback(session, responses):
    # creating a tag that already exists in edx-platform: we'll make sure
    # that edx-platform is attempted *last*
    ordered_commits = OrderedDict(
        sorted(expected_commits.items(), key=lambda x: x[0], reverse=False)
    )
    with pytest.raises(RuntimeError) as excinfo:
        create_ref_for_repos(
            ordered_commits,
            "tag-exists-some-repos",
            session,
            rollback_on_fail=False
        )
    assert len(responses.calls) == 3
    assert responses.calls[0].request.url == "https://api.github.com/repos/edx/XBlock/git/refs"
    xb_payload = json.loads(responses.calls[0].request.body)
    assert xb_payload == {
        "sha": "1a2b3c4d5e6f",
        "ref": "refs/tags/tag-exists-some-repos",
    }
    assert responses.calls[1].request.url == "https://api.github.com/repos/edx/configuration/git/refs"
    conf_payload = json.loads(responses.calls[1].request.body)
    assert conf_payload == {
        "sha": "12345deadbeef",
        "ref": "refs/tags/tag-exists-some-repos",
    }
    assert responses.calls[2].request.url == "https://api.github.com/repos/edx/edx-platform/git/refs"
    plat_payload = json.loads(responses.calls[2].request.body)
    assert plat_payload == {
        "sha": "deadbeef12345",
        "ref": "refs/tags/tag-exists-some-repos",
    }
    assert "No rollback attempted" in str(excinfo.value)
    assert "Reference already exists" in str(excinfo.value)
    assert "Refs exist on the following repos: edx/XBlock, edx/configuration" in str(excinfo.value)


def test_create_existing_tag_at_end_rollback_failure(session, responses):
    # creating a tag that already exists in edx-platform: we'll make sure
    # that edx-platform is attempted *last*
    ordered_commits = OrderedDict(
        sorted(expected_commits.items(), key=lambda x: x[0], reverse=False)
    )

    # when we try to delete the configuration tag, it will fail with a 500 error
    responses.add(
        responses.DELETE,
        "https://api.github.com/repos/edx/configuration/git/refs/tags/tag-exists-some-repos",
        status=500,
    )

    ### DANGER: ACCESSING PRIVATE APIS FOR RESPONSES LIBRARY ###
    # grab the object we just created
    last_responses_url_obj = responses._default_mock._urls[-1]
    # move it to the front, so it matches *first*
    responses._default_mock._urls.insert(0, last_responses_url_obj)
    ### END PRIVATE API ACCESS FOR RESPONSES LIBRARY ###

    with pytest.raises(RuntimeError) as excinfo:
        create_ref_for_repos(
            ordered_commits,
            "tag-exists-some-repos",
            session,
        )
    assert len(responses.calls) == 5
    assert responses.calls[0].request.url == "https://api.github.com/repos/edx/XBlock/git/refs"
    xb_payload = json.loads(responses.calls[0].request.body)
    assert xb_payload == {
        "sha": "1a2b3c4d5e6f",
        "ref": "refs/tags/tag-exists-some-repos",
    }
    assert responses.calls[1].request.url == "https://api.github.com/repos/edx/configuration/git/refs"
    conf_payload = json.loads(responses.calls[1].request.body)
    assert conf_payload == {
        "sha": "12345deadbeef",
        "ref": "refs/tags/tag-exists-some-repos",
    }
    assert responses.calls[2].request.url == "https://api.github.com/repos/edx/edx-platform/git/refs"
    plat_payload = json.loads(responses.calls[2].request.body)
    assert plat_payload == {
        "sha": "deadbeef12345",
        "ref": "refs/tags/tag-exists-some-repos",
    }
    # third response failed, so try to rollback. XBlock succeeds...
    assert responses.calls[3].request.url == "https://api.github.com/repos/edx/XBlock/git/refs/tags/tag-exists-some-repos"
    assert responses.calls[3].request.method == 'DELETE'
    assert responses.calls[4].request.url == "https://api.github.com/repos/edx/configuration/git/refs/tags/tag-exists-some-repos"
    assert responses.calls[4].request.method == 'DELETE'
    # ... but configuration fails, so we get an exception
    assert "failed to delete ref on the following repos: edx/configuration" in str(excinfo)


def test_remove_all(session, responses):
    repo_names = ["edx/edx-platform", "edx/configuration", "edx/XBlock"]
    result = remove_ref_for_repos(repo_names, "tag-exists-all-repos", session)
    assert result is True
    assert len(responses.calls) == 3
    assert responses.calls[0].request.url == "https://api.github.com/repos/edx/edx-platform/git/refs/tags/tag-exists-all-repos"
    assert responses.calls[0].request.method == "DELETE"
    assert responses.calls[1].request.url == "https://api.github.com/repos/edx/configuration/git/refs/tags/tag-exists-all-repos"
    assert responses.calls[1].request.method == "DELETE"
    assert responses.calls[2].request.url == "https://api.github.com/repos/edx/XBlock/git/refs/tags/tag-exists-all-repos"
    assert responses.calls[2].request.method == "DELETE"


def test_remove_some(session, responses):
    repo_names = ["edx/edx-platform", "edx/configuration", "edx/XBlock"]
    result = remove_ref_for_repos(repo_names, "tag-exists-some-repos", session)
    assert result is True
    assert len(responses.calls) == 3
    assert responses.calls[0].request.url == "https://api.github.com/repos/edx/edx-platform/git/refs/tags/tag-exists-some-repos"
    assert responses.calls[0].request.method == "DELETE"
    assert responses.calls[1].request.url == "https://api.github.com/repos/edx/configuration/git/refs/tags/tag-exists-some-repos"
    assert responses.calls[1].request.method == "DELETE"
    assert responses.calls[2].request.url == "https://api.github.com/repos/edx/XBlock/git/refs/tags/tag-exists-some-repos"
    assert responses.calls[2].request.method == "DELETE"


def test_remove_none(session, responses):
    repo_names = ["edx/edx-platform", "edx/configuration", "edx/XBlock"]
    result = remove_ref_for_repos(repo_names, "tag-exists-no-repos", session)
    assert result is False
    assert len(responses.calls) == 3
    assert responses.calls[0].request.url == "https://api.github.com/repos/edx/edx-platform/git/refs/tags/tag-exists-no-repos"
    assert responses.calls[0].request.method == "DELETE"
    assert responses.calls[1].request.url == "https://api.github.com/repos/edx/configuration/git/refs/tags/tag-exists-no-repos"
    assert responses.calls[1].request.method == "DELETE"
    assert responses.calls[2].request.url == "https://api.github.com/repos/edx/XBlock/git/refs/tags/tag-exists-no-repos"
    assert responses.calls[2].request.method == "DELETE"


def test_remove_with_errors(session, responses):
    repo_names = ["edx/edx-platform", "edx/configuration", "edx/XBlock"]

    # when we try to delete the edx-platform tag, it will fail with a 500 error
    responses.add(
        responses.DELETE,
        "https://api.github.com/repos/edx/edx-platform/git/refs/tags/tag-exists-all-repos",
        status=500,
    )

    ### DANGER: ACCESSING PRIVATE APIS FOR RESPONSES LIBRARY ###
    # grab the object we just created
    last_responses_url_obj = responses._default_mock._urls[-1]
    # move it to the front, so it matches *first*
    responses._default_mock._urls.insert(0, last_responses_url_obj)
    ### END PRIVATE API ACCESS FOR RESPONSES LIBRARY ###

    with pytest.raises(RuntimeError) as excinfo:
        remove_ref_for_repos(repo_names, "tag-exists-all-repos", session)

    assert len(responses.calls) == 3
    assert responses.calls[0].request.url == "https://api.github.com/repos/edx/edx-platform/git/refs/tags/tag-exists-all-repos"
    assert responses.calls[0].request.method == "DELETE"
    assert responses.calls[1].request.url == "https://api.github.com/repos/edx/configuration/git/refs/tags/tag-exists-all-repos"
    assert responses.calls[1].request.method == "DELETE"
    assert responses.calls[2].request.url == "https://api.github.com/repos/edx/XBlock/git/refs/tags/tag-exists-all-repos"
    assert responses.calls[2].request.method == "DELETE"
    assert "Failed to remove the ref from the following repos: edx/edx-platform" in str(excinfo)
