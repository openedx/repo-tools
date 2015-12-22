import pytest
import json
import re
import requests
import textwrap
import responses as resp_module


@pytest.fixture
def session():
    return requests.Session()


@pytest.fixture
def responses(request):
    resp_module.start()
    def done():
        resp_module.stop()
        resp_module.reset()
    request.addfinalizer(done)
    return resp_module


@pytest.fixture
def common_mocks(mocker, responses):
    mocker.patch("tag_release.get_github_creds", return_value=("user", "pass"))

    fake_repos = textwrap.dedent("""
        edx/edx-platform:
            openedx-release:
                ref: release
                requirements: requirements/edx/github.txt
        edx/configuration:
            openedx-release:
                ref: master
        edx/XBlock:
            openedx-release:
                parent-repo: edx/edx-platform
        edx/unrelated:
            track-pulls: true
    """)
    responses.add(
        responses.GET,
        "https://raw.githubusercontent.com/edx/repo-tools-data/master/repos.yaml",
        body=fake_repos,
    )

    repo_refs = {
        "edx/edx-platform": {
            "refs/tags/tag-exists-all-repos": "7878787",
            "refs/tags/tag-exists-some-repos": "65656565",
        },
        "edx/configuration": {
            "refs/tags/tag-exists-all-repos": "34233423"
        },
        "edx/XBlock": {
            "refs/tags/tag-exists-all-repos": "987078987",
            "refs/tags/0.4.4": "1a2b3c4d5e6f",
        }
    }
    index_ref_url_re = re.compile(r"""
        https://api\.github\.com/repos/
        (?P<owner>[a-zA-Z0-9_.-]+)/
        (?P<repo>[a-zA-Z0-9_.-]+)/
        git/refs
    """, re.VERBOSE)
    ref_url_re = re.compile(r"""
        https://api\.github\.com/repos/
        (?P<owner>[a-zA-Z0-9_.-]+)/
        (?P<repo>[a-zA-Z0-9_.-]+)/
        git/refs/
        (?P<type>tags|heads)/
        (?P<name>[a-zA-Z0-9_./-]+)
    """, re.VERBOSE)


    def get_ref_callback(request):
        match = ref_url_re.match(request.url)
        name = match.group('name')
        ref_type = match.group('type')
        ref = "refs/{type}/{name}".format(
            type=ref_type,
            name=name,
        )
        owner = match.group('owner')
        repo = match.group('repo')
        full_repo_name = "{owner}/{repo}".format(owner=owner, repo=repo)
        sha = repo_refs.get(full_repo_name, {}).get(ref, "")
        if sha:
            commit_url = "https://api.github.com/repos/{owner}/{repo}/git/commits/{sha}".format(
                owner=owner,
                repo=repo,
                sha=sha
            )
            ret_payload = {
                "ref": ref,
                "object": {
                    "type": "commit",
                    "url": commit_url,
                }
            }
            return 200, {"Content-Type": "application/json"}, json.dumps(ret_payload)
        else:
            return 404, {}, ''

    responses.add_callback(
        responses.GET, ref_url_re, callback=get_ref_callback,
    )

    def create_ref_callback(request):
        match = index_ref_url_re.match(request.url)
        owner = match.group('owner')
        repo = match.group('repo')
        full_repo_name = "{owner}/{repo}".format(owner=owner, repo=repo)
        payload = json.loads(request.body)
        ref = payload["ref"]
        if ref not in repo_refs.get(full_repo_name, {}):
            # create the ref
            sha = payload["sha"]
            repo_refs[full_repo_name][ref] = sha
            tag_url = "https://api.github.com/repos/{full_repo}/git/{ref}".format(
                full_repo=full_repo_name,
                ref=ref,
            )
            ret_payload = {
                "ref": ref,
                "url": tag_url,
                "object": {
                    "sha": sha,
                    "type": "commit"
                }
            }
            headers = {
                "Location": tag_url,
                "Content-Type": "application/json",
            }
            return 201, headers, json.dumps(ret_payload)
        else:
            # tag already exists
            return 422, {"Content-Type": "application/json"}, json.dumps({"message": "Reference already exists"})

    responses.add_callback(
        responses.POST, index_ref_url_re, callback=create_ref_callback,
    )

    def delete_ref_callback(request):
        match = ref_url_re.match(request.url)
        name = match.group('name')
        ref_type = match.group('type')
        ref = "refs/{type}/{name}".format(
            type=ref_type,
            name=name,
        )
        owner = match.group('owner')
        repo = match.group('repo')
        full_repo_name = "{owner}/{repo}".format(owner=owner, repo=repo)
        if ref in repo_refs.get(full_repo_name, {}):
            del repo_refs[full_repo_name][ref]
            return 204, {}, ''
        else:
            return 422, {"Content-Type": "application/json"}, json.dumps({"message": "Reference does not exist"})

    responses.add_callback(
        responses.DELETE, ref_url_re, callback=delete_ref_callback,
    )

    repo_url_tpl = "https://api.github.com/repos/{full_repo}"
    for repo_name in repo_refs:
        responses.add(responses.GET, repo_url_tpl.format(full_repo=repo_name), status=200)

    platform_release_branch = {
        "name": "release",
        "commit": {
            "sha": "deadbeef12345",
            "commit": {
                "author": {
                    "name": "Dev 1"
                },
                "committer": {
                    "name": "Dev 1",
                },
                "message": "commit message for edx-platform release commit"
            }
        }
    }
    branch_url = "https://api.github.com/repos/edx/edx-platform/branches/release"
    responses.add(responses.GET, branch_url, json=platform_release_branch)

    configuration_master_branch = {
        "name": "master",
        "commit": {
            "sha": "12345deadbeef",
            "commit": {
                "author": {
                    "name": "Dev 2"
                },
                "committer": {
                    "name": "Dev 2",
                },
                "message": "commit message for configuration master commit"
            }
        }
    }
    branch_url = "https://api.github.com/repos/edx/configuration/branches/master"
    responses.add(responses.GET, branch_url, json=configuration_master_branch)

    github_txt = textwrap.dedent("""
        git+https://github.com/edx/XBlock.git@0.4.4#egg=XBlock==0.4.4
    """)
    github_txt_url = "https://raw.githubusercontent.com/edx/edx-platform/release/requirements/edx/github.txt"
    responses.add(responses.GET, github_txt_url, body=github_txt)

    xblock_tag_commit_url = "https://api.github.com/repos/edx/XBlock/git/commits/1a2b3c4d5e6f"
    xblock_tag_commit = {
        "sha": "1a2b3c4d5e6f",
        "author": {
            "name": "Dev 3"
        },
        "committer": {
            "name": "Dev 3",
        },
        "message": "commit message for XBlock at 0.4.4 tag",
    }
    xblock_branch_url = "https://api.github.com/repos/edx/XBlock/branches/0.4.4"
    responses.add(responses.GET, xblock_branch_url, status=404)
    responses.add(responses.GET, xblock_tag_commit_url, json=xblock_tag_commit)
