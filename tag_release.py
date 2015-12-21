#!/usr/bin/env python
"""
Tag repos for an Open edX release. When run, this script will:

1. Make sure we have an OAuth token for the GitHub API, and help the user
   create one if we don't already have one
2. Fetch the repos.yaml file from the repo-tools-data repo
3. Identify the repos in that file that are tagged in the Open edX release
4. Identify the commit that needs to be tagged in each repo, tracing cross-repo
   dependencies as necessary
5. Show the identified repos and commits, and ask for confirmation from the user
6. Upon confirmation, create Git tags for the repos using the GitHub API
"""
from __future__ import unicode_literals, print_function
import sys
import re
import json
import getpass
import argparse
import logging
import copy
try:
    from path import Path as path
    from git import Repo, Commit
    from git.refs.symbolic import SymbolicReference
    from git.exc import GitCommandError
    import requests
    from requests.exceptions import RequestException
    import yaml
except ImportError:
    print("Error: missing dependencies! Please run this command to install them:")
    print("pip install path.py requests GitPython PyYAML")
    sys.exit(1)

log = logging.getLogger(__name__)


# Name used for fetching/storing GitHub OAuth tokens on disk
TOKEN_NAME = "openedx-release"
# URL to the source of truth about our repositories
REPOS_YAML = "https://raw.githubusercontent.com/edx/repo-tools-data/master/repos.yaml"
# Regular expression for parsing out the parts of a pip requirement line
REQUIREMENT_RE = re.compile(r"""
    git\+https?://github\.com/          # prefix
    (?P<owner>[a-zA-Z0-9_.-]+)/         # repo owner
    (?P<repo>[a-zA-Z0-9_.-]+).git       # repo name
    (@(?P<ref>[a-zA-Z0-9_.-]+))?        # git ref (tag, branch, or commit hash) (optional)
    (\#egg=(?P<egg>[a-zA-Z0-9_.-]+))?   # egg name (optional)
    (==(?P<version>[a-zA-Z0-9_.-]+))?   # version (optional)
""", re.VERBOSE)


def make_parser():
    parser = argparse.ArgumentParser(
        description="Tag GitHub repos for Open edX releases",
    )
    parser.add_argument(
        'tag', metavar="REFNAME",
        help="The name of the ref to create in the repos",
    )

    refgroup = parser.add_argument_group(
        "arguments for git refs",
    )
    # reftype = refgroup.add_mutually_exclusive_group()
    # reftype.add_argument(
    #     '--tag', action="store_true", default=True, dest="use_tag",
    #     help="Create tags in repos [default]"
    # )
    # reftype.add_argument(
    #     '--branch', action="store_false", default=True, dest="use_tag",
    #     help="Create branches in repos"
    # )
    refgroup.add_argument(
        '--override-ref', nargs=1, metavar="REF",
        help="A reference to use that overrides the references from the "
            "repos.yaml file in *ALL* repos. This might be a release candidate "
            "branch, for example."
    )
    refgroup.add_argument(
        '--override', nargs=2, metavar=("REPO", "REF"),
        action="append", dest="overrides",
        help="Override a reference for a specific repo. The repo must be "
            "specified using the full name of the repo, like 'edx/edx-platform'. "
            "This option can be provided multiple times."
    )

    parser.add_argument(
        '-y', '--yes', action="store_false", default=True, dest="interactive",
        help="non-interactive mode: answer yes to all questions",
    )
    parser.add_argument(
        '-q', '--quiet', action="store_true", default=False,
        help="don't print any unnecessary output"
    )
    parser.add_argument(
        '-R', '--reverse', action="store_true", default=False,
        help="delete tag instead of creating it"
    )
    parser.add_argument(
        '--skip-invalid', action="store_true", default=False,
        help="if the repos.yaml file points to an invalid repo, skip it "
            "instead of throwing an error"
    )

    return parser


def get_github_creds():
    """
    Returns GitHub credentials if they exist, as a two-tuple of (username, token).
    Otherwise, return None.
    """
    netrc_auth = requests.utils.get_netrc_auth("https://api.github.com")
    if netrc_auth:
        return netrc_auth
    config_file = (path("~/.config") / TOKEN_NAME).expand()
    if config_file.isfile():
        with open(config_file) as f:
            config = json.load(f)
        github_creds = config.get("credentials", {}).get("api.github.com", {})
        username = github_creds.get("username", "")
        token = github_creds.get("token", "")
        if username and token:
            return (username, token)
    return None


def create_github_creds():
    """
    https://developer.github.com/v3/oauth_authorizations/#create-a-new-authorization
    """
    headers = {"User-Agent": TOKEN_NAME}
    payload = {
        "note": TOKEN_NAME,
        "scopes": ["repo"],
    }
    username = raw_input("GitHub username: ")
    password = getpass.getpass("GitHub password: ")
    response = requests.post(
        "https://api.github.com/authorizations",
        auth=(username, password),
        headers=headers, json=payload,
    )
    # is the user using two-factor authentication?
    otp_header = response.headers.get("X-GitHub-OTP")
    if not response.ok and otp_header and otp_header.startswith("required;"):
        # get two-factor code, redo the request
        headers["X-GitHub-OTP"] = raw_input("Two-factor authentication code: ")
        response = requests.post(
            "https://api.github.com/authorizations",
            auth=(username, password),
            headers=headers, json=payload,
        )
    if not response.ok:
        message = response.json()["message"]
        if message != "Validation Failed":
            raise requests.exceptions.RequestException(message)
        else:
            # A token with this TOKEN_NAME already exists on GitHub.
            # Delete it, and try again.
            token_id = get_github_auth_id(username, password, TOKEN_NAME)
            if token_id:
                delete_github_auth_token(username, password, token_id)
            response = requests.post(
                "https://api.github.com/authorizations",
                auth=(username, password),
                headers=headers, json=payload,
            )
    if not response.ok:
        message = response.json()["message"]
        raise requests.exceptions.RequestException(message)

    return (username, response.json()["token"])


def get_github_auth_id(username, password, note):
    """
    Return the ID associated with the GitHub auth token with the given note.
    If no such auth token exists, return None.
    """
    response = requests.get(
        "https://api.github.com/authorizations",
        auth=(username, password),
        headers={"User-Agent": TOKEN_NAME},
    )
    if not response.ok:
        message = response.json()["message"]
        raise requests.exceptions.RequestException(message)

    for auth_token in response.json():
        if auth_token["note"] == TOKEN_NAME:
            return auth_token["id"]
    return None


def delete_github_auth_token(username, password, token_id):
    response = requests.delete(
        "https://api.github.com/authorizations/{id}".format(id=token_id),
        auth=(username, password),
        headers={"User-Agent": TOKEN_NAME},
    )
    if not response.ok:
        message = response.json()["message"]
        raise requests.exceptions.RequestException(message)


def ensure_github_creds(attempts=3):
    """
    Make sure that we have GitHub OAuth credentials. This will check the user's
    .netrc file, as well as the ~/.config/openedx-release file. If no credentials
    exist in either place, it will prompt the user to create OAuth credentials,
    and store them in ~/.config/openedx-release.

    Returns False if we found credentials, True if we had to create them.
    """
    if get_github_creds():
        return False

    # Looks like we need to create the OAuth creds
    print("We need to set up OAuth authentication with GitHub's API. "
          "Your password will not be stored.", file=sys.stderr)
    token = None
    for _ in range(attempts):
        try:
            username, token = create_github_creds()
        except requests.exceptions.RequestException as e:
            print(
                "Invalid authentication: {}".format(e.message),
                file=sys.stderr,
            )
            continue
        else:
            break
    if token:
        print("Successfully authenticated to GitHub", file=sys.stderr)
    if not token:
        print("Too many invalid authentication attempts.", file=sys.stderr)
        return False

    config_file = (path("~/.config") / TOKEN_NAME).expand()
    # make sure parent directory exists
    config_file.parent.makedirs_p()
    # read existing config if it exists
    if config_file.isfile():
        with open(config_file) as f:
            config = json.load(f)
    else:
        config = {}
    # update config
    if 'credentials' not in config:
        config["credentials"] = {}
    if 'api.github.com' not in config['credentials']:
        config["credentials"]["api.github.com"] = {}
    config["credentials"]["api.github.com"]["username"] = username
    config["credentials"]["api.github.com"]["token"] = token
    # write it back out
    with open(config_file, "w") as f:
        json.dump(config, f)

    return True


def openedx_release_repos(session):
    """
    Return a subset of the repos listed in the repos.yaml file: the repos
    with an `openedx-release` section.
    """
    repos_resp = session.get(REPOS_YAML)
    repos_resp.raise_for_status()
    all_repos = yaml.safe_load(repos_resp.text)
    repos = {name: data for name, data in all_repos.items()
             if data and data.get("openedx-release")}
    return repos


def override_repo_refs(repos, override_ref=None, overrides=None):
    """
    Returns a new `repos` dictionary with the CLI overrides applied.
    """
    overrides = overrides or {}
    if not override_ref and not overrides:
        return repos

    repos_copy = copy.deepcopy(repos)
    for repo_name, repo_data in repos.items():
        if not repo_data:
            continue
        release_data = repo_data.get("openedx-release")
        if not release_data:
            continue
        local_override = overrides.get(repo_name, override_ref)
        if local_override:
            repos_copy[repo_name]["openedx-release"]["ref"] = local_override
            if "parent-repo" in repos_copy[repo_name]["openedx-release"]:
                del repos_copy[repo_name]["openedx-release"]["parent-repo"]

    return repos_copy


def commits_to_tag_in_repos(repos, session, skip_invalid=False):
    """
    Returns a dictionary of information about what commit should be tagged
    for each repository passed into this function. The return type is as
    follows:

    {
        "full_repo_name": {
            "ref": "name of tag or branch"
            "ref_type": "tag", # or "branch"
            "sha": "1234566789abcdef",
            "message": "The commit message"
            "author": {
                "name": "author's name",
                "email": "author's email"
            }
            "committer": {
                "name": "committer's name",
                "email": "committer's email",
            }
        },
        "next_repo_name": {...}
    }

    If the information in the passed-in dictionary is invalid in any way,
    this function will throw an error unless `skip_invalid` is set to True,
    in which case the invalid information will simply be logged and ignored.
    """
    to_tag = {}
    for repo_name, repo_data in repos.items():
        # make sure the repo exists
        repo_url = "https://api.github.com/repos/{repo}".format(repo=repo_name)
        repo_resp = session.get(repo_url)
        if not repo_resp.ok:
            msg = "Invalid repo {repo}".format(repo=repo_name)
            if skip_invalid:
                log.error(msg)
                continue
            else:
                raise RuntimeError(msg)
        # are we specifying a ref?
        ref_name = repo_data["openedx-release"].get("ref")
        if ref_name:
            try:
                to_tag[repo_name] = get_latest_commit_for_ref(
                    repo_name,
                    ref_name,
                    session=session,
                )
            except RequestException, ValueError:
                if skip_invalid:
                    msg = "Invalid ref {ref} in repo {repo}".format(
                        ref=ref_name,
                        repo=repo_name,
                    )
                    log.error(msg)
                    continue
                else:
                    raise
        # are we specifying a parent repo?
        parent_repo_name = repo_data["openedx-release"].get("parent-repo")
        if parent_repo_name:
            # we need the ref for the parent repo
            parent_release_data = repos[parent_repo_name]["openedx-release"]
            parent_ref = parent_release_data["ref"]
            requirements_file = parent_release_data.get("requirements", "requirements.txt")

            try:
                to_tag[repo_name] = get_latest_commit_for_parent_repo(
                    repo_name,
                    parent_repo_name,
                    parent_ref,
                    requirements_file,
                    session=session,
                )
            except RequestException, ValueError:
                if skip_invalid:
                    msg = "Problem getting parent ref for repo {repo}".format(
                        repo=repo_name,
                    )
                    log.error(msg)
                    continue
                else:
                    raise
    return to_tag


def get_latest_commit_for_ref(repo_name, ref, session):
    """
    Given a repo name and a ref in that repo, return some information about
    the commit that the ref refers to. This function is called by
    commits_to_tag_in_repos(), and it returns information in the same structure.
    """
    # is it a branch?
    branch_url = "https://api.github.com/repos/{repo}/branches/{branch}".format(
        repo=repo_name,
        branch=ref,
    )
    branch_resp = session.get(branch_url)
    if branch_resp.ok:
        branch = branch_resp.json()
        commit = branch["commit"]["commit"]
        return {
            "ref": ref,
            "ref_type": "branch",
            "sha": branch["commit"]["sha"],
            "message": commit["message"],
            "author": commit["author"],
            "committer": commit["committer"],
        }

    if branch_resp.status_code != 404:
        # This is not a simple "branch not found" error, it's something
        # worse, like a 500 Server Error or a flaky network. Raise the error.
        branch_resp.raise_for_status()

    # is it a tag?
    tag_url = "https://api.github.com/repos/{repo}/git/refs/tags/{tag}".format(
        repo=repo_name,
        tag=ref,
    )
    tag_resp = session.get(tag_url)
    if tag_resp.ok:
        tag = tag_resp.json()
        if tag["object"]["type"] == "tag":
            # An annotated tag, one more level of indirection.
            tag_resp = session.get(tag["object"]["url"])
            tag_resp.raise_for_status()
            tag = tag_resp.json()
        # need to do a subsequent API call to get the tagged commit
        commit_url = tag["object"]["url"]
        commit_resp = session.get(commit_url)
        if commit_resp.ok:
            commit = commit_resp.json()
            return {
                "ref": ref,
                "ref_type": "tag",
                "sha": commit["sha"],
                "message": commit["message"],
                "author": commit["author"],
                "committer": commit["committer"],
            }

    if tag_resp.status_code != 404:
        # This is not a simple "tag not found" error, it's something
        # worse, like a 500 Server Error or a flaky network. Raise the error.
        tag_resp.raise_for_status()

    msg = "No commit for {ref} in {repo}".format(
        ref=ref, repo=repo_name,
    )
    raise ValueError(msg)


def get_latest_commit_for_parent_repo(
        repo_name, parent_repo_name, parent_ref, requirements_file, session,
    ):
    """
    Some repos point to other repos via requirements files. For example,
    edx/edx-platform points to edx/XBlock and edx/edx-ora2 via the github.txt
    requirement file. This function takes two repo names: the target, and the
    target's parent. (In this case, "edx/XBlock" could be the target, and
    "edx/edx-platform" would be its parent.) This function looks up what
    reference the parent uses to point at the target, and looks up the commit
    that the reference points to in the target repo.

    This function is called by commits_to_tag_in_repos(),
    and it returns information in the same structure.
    """
    req_file_url = "https://raw.githubusercontent.com/{parent_repo}/{ref}/{req_file}".format(
        parent_repo=parent_repo_name,
        ref=parent_ref,
        req_file=requirements_file,
    )
    req_file_resp = session.get(req_file_url)
    req_file_resp.raise_for_status()
    ref = get_ref_for_dependency(req_file_resp.text, repo_name, parent_repo_name)
    return get_latest_commit_for_ref(repo_name, ref, session=session)


def get_ref_for_dependency(requirements_text, repo_name, parent_repo_name=None):
    requirements_lines = requirements_text.splitlines()
    # strip lines that are empty, or start with comments
    relevant_lines = [line for line in requirements_lines
                      if line and not line.isspace() and not line.startswith("#")]

    # find the line that corresponds to this repo
    repo_lines = [line for line in relevant_lines if repo_name in line]
    if not repo_lines:
        msg = "{repo_name} dependency not found in {parent} repo".format(
            repo_name=repo_name, parent=parent_repo_name,
        )
        raise ValueError(msg)
    if len(repo_lines) > 1:
        msg = "multiple {repo_name} dependencies found in {parent} repo".format(
            repo_name=repo_name, parent=parent_repo_name,
        )
        raise ValueError(msg)

    dependency_line = repo_lines[0]
    # parse out the branch/tag
    match = REQUIREMENT_RE.search(dependency_line)
    if match:
        ref = match.group('ref')
    else:
        ref = None
    if not ref:
        msg = "no reference found for {repo_name} dependency in {parent} repo".format(
            repo_name=repo_name, parent=parent_repo_name,
        )
        raise ValueError(msg)
    return ref


def tag_exists_in_repo(tag, repo, session):
    """
    Returns a boolean indicating whether the given tag already exists in the
    given repo.
    """
    tag_url = "https://api.github.com/repos/{repo}/git/refs/tags/{tag}".format(
        repo=repo,
        tag=tag,
    )
    tag_resp = session.get(tag_url)
    return tag_resp.ok


def repos_where_tag_exists(tag, repos, session):
    return [repo for repo in repos if tag_exists_in_repo(tag, repo, session)]


def todo_list(to_tag):
    """
    Returns a string, suitable to be printed on the command line,
    that contains a record of the repos and commits that are about to be tagged.
    If no tag info is passed in, return None.
    """
    if not to_tag:
        return None

    lines = []
    for repo_name, commit_info in to_tag.items():
        lines.append("{repo}: {ref} ({type}) {sha}".format(
            repo=repo_name,
            ref=commit_info['ref'],
            type=commit_info['ref_type'],
            sha=commit_info['sha'][0:7],
        ))
        lines.append("  " + commit_info["message"].splitlines()[0])
    return "\n".join(lines)


def tag_repos(to_tag, tag_name, session, rollback_on_fail=True):
    """
    Actually tag the repos with the given tag name.
    If `rollback_on_fail` is True, then on any failure, try to delete the tags
    that we're just created, so that we don't fail in a partially-completed
    state. (Note that this is *not* a reliable rollback -- other people could
    have already fetched the tags from GitHub, or the deletion attempt might
    itself fail!)

    If this function succeeds, it will return True. If this function fails,
    but the world is in a consistent state, this function will return False.
    The world is consistent if *no* repos were successfully tagged in the first
    place, or all repos that were originally tagged were successfully rolled
    back (because `rollback_on_fail` is set to True). If this function fails,
    and the world is in an inconsistent state, this function will raise a
    RuntimeError. This could happen if some (but not all) of the tags are created,
    and either rollback is not attempted (because `rollback_on_fail` is set to
    False), or rollback fails.
    """
    succeeded = []
    failed_resp = None
    failed_repo = None
    ref_name = "refs/tags/{name}".format(name=tag_name)
    for repo_name, commit_info in to_tag.items():
        ref_url = "https://api.github.com/repos/{repo}/git/refs".format(repo=repo_name)
        payload = {
            "ref": ref_name,
            "sha": commit_info['sha'],
        }
        resp = session.post(ref_url, json=payload)
        if resp.ok:
            succeeded.append(repo_name)
        else:
            failed_resp = resp
            failed_repo = repo_name
            # don't try to tag any others, just stop
            break

    if failed_resp is None:
        return True

    # if we got to this point, then there was a failure.
    try:
        original_err_msg = failed_resp.json()["message"]
    except Exception:
        original_err_msg = failed_resp.text

    if not succeeded:
        msg = (
            "Failed to create {ref_name} on {failed_repo}. "
            "Error was {orig_err}. No tags have been created on any repos."
        ).format(
            ref_name=ref_name,
            failed_repo=failed_repo,
            orig_err=original_err_msg,
        )
        log.error(msg)
        return False

    if rollback_on_fail:
        rollback_failures = []
        for repo_name in succeeded:
            ref_url = "https://api.github.com/repos/{repo}/git/{ref_name}".format(
                repo=repo_name,
                ref_name=ref_name,
            )
            resp = session.delete(ref_url)
            if not resp.ok:
                rollback_failures.append(repo_name)

        if rollback_failures:
            msg = (
                "Failed to create {ref_name} on {failed_repo}. "
                "Error was {orig_err}. "
                "Attempted to roll back, but failed to delete tag on "
                "the following repos: {rollback_failures}"
            ).format(
                ref_name=ref_name,
                failed_repo=failed_repo,
                orig_err=original_err_msg,
                rollback_failures=", ".join(rollback_failures)
            )
            err = RuntimeError(msg)
            err.response = failed_resp
            err.repos = rollback_failures
            raise err
        else:
            msg = (
                "Failed to create {ref_name} on {failed_repo}. "
                "Error was {orig_err}. However, all refs were successfully "
                "rolled back."
            ).format(
                ref_name=ref_name,
                failed_repo=failed_repo,
                orig_err=original_err_msg,
            )
            log.error(msg)
            return False
    else:
        # don't try to rollback, just raise an error
        msg = (
            "Failed to create {ref_name} on {failed_repo}. "
            "Error was {orig_err}. No rollback attempted. Tags exist on "
            "the following repos: {tagged_repos}"
        ).format(
            ref_name=ref_name,
            failed_repo=failed_repo,
            orig_err=original_err_msg,
            tagged_repos=", ".join(succeeded)
        )
        err = RuntimeError(msg)
        err.response = failed_resp
        err.repos = succeeded
        raise err


def untag_repos(repo_names, tag_name, session):
    """
    Given an iterable of repository full names (like "edx/edx-platform") and
    a tag name, this function attempts to delete the named tag from each
    GitHub repository listed in the iterable. If the tag does not exist on
    the repo, it is skipped.

    This function returns True if any repos were untagged, or False if no repos
    were modified. If an error occurs while trying to untag a repo, the function
    will continue trying to untag all the other repos in the iterable -- but
    after all repos have been attempted, this function will raise a RuntimeError
    with a list of all the repos that were not untagged. Trying to remove a tag
    from a repo that does not have that tag to begin with is *not* treated as
    an error.
    """
    failures = {}
    modified = False
    for repo_name in repo_names:
        ref_url = "https://api.github.com/repos/{repo}/git/{ref_name}".format(
            repo=repo_name,
            ref_name="refs/tags/{tag}".format(tag=tag_name),
        )
        resp = session.delete(ref_url)
        if resp.ok:
            # successfully deleted -- we modified a repo
            modified = True

        elif resp.status_code == 422:
            # error message: "Reference does not exist"
            # tag didn't exist to begin with; not an error
            pass

        else:
            # Oops, we got a failure. Record it and move on.
            failures[repo_name] = resp

    if failures:
        msg = (
            "Failed to untag the following repos: {repos}"
        ).format(
            repos=", ".join(failures.keys())
        )
        err = RuntimeError(msg)
        err.failures = failures
        raise err

    return modified


def main():
    parser = make_parser()
    args = parser.parse_args()

    ensure_github_creds()
    username, token = get_github_creds()
    session = requests.Session()
    session.headers["Authorization"] = "token {}".format(token)
    session.headers["User-Agent"] = TOKEN_NAME

    repos = openedx_release_repos(session)
    if not repos:
        raise ValueError("No repos marked for openedx-release in repos.yaml!")

    if args.reverse:
        modified = untag_repos(repos, args.tag, session)
        if not args.quiet:
            if modified:
                print("{tag} tag removed from {repos}".format(
                    tag=args.tag,
                    repos=", ".join(repos.keys())
                ))
            else:
                print("No tags modified")
        return modified

    already_exists = repos_where_tag_exists(args.tag, repos, session)
    if already_exists:
        msg = (
            "The {tag} tag already exists in the following repos: {repos}"
        ).format(
            tag=args.tag,
            repos=", ".join(already_exists),
        )
        raise ValueError(msg)

    repos = override_repo_refs(
        repos,
        override_ref=args.override_ref,
        overrides=dict(args.overrides or ()),
    )

    to_tag = commits_to_tag_in_repos(repos, session, skip_invalid=args.skip_invalid)
    if args.interactive or not args.quiet:
        print(todo_list(to_tag))
    if args.interactive:
        response = raw_input("Is this correct? [y/N] ")
        if response.lower() not in ("y", "yes", "1"):
            return

    result = tag_repos(to_tag, args.tag, session)
    if not args.quiet:
        if result:
            print("Success!")
        else:
            print("Failed to tag repos, but rolled back successfully")
    return result


if __name__ == "__main__":
    main()
