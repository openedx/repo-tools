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

import copy
import datetime
import logging
import re

import click
from edx_repo_tools.auth import pass_github
from edx_repo_tools.data import iter_openedx_yaml
from edx_repo_tools.utils import dry, dry_echo
from github3 import GitHubError

log = logging.getLogger(__name__)


# Name used for fetching/storing GitHub OAuth tokens on disk
TOKEN_NAME = "openedx-release"
# Regular expression for parsing out the parts of a pip requirement line
REQUIREMENT_RE = re.compile(r"""
    git\+https?://github\.com/          # prefix
    (?P<owner>[a-zA-Z0-9_.-]+)/         # repo owner
    (?P<repo>[a-zA-Z0-9_.-]+).git       # repo name
    (@(?P<ref>[a-zA-Z0-9_.-]+))?        # git ref (tag, branch, or commit hash) (optional)
    (\#egg=(?P<egg>[a-zA-Z0-9_.-]+))?   # egg name (optional)
    (==(?P<version>[a-zA-Z0-9_.-]+))?   # version (optional)
""", re.VERBOSE)


def openedx_release_repos(hub):
    """
    Return a subset of the repos listed in the repos.yaml file: the repos
    with an `openedx-release` section.
    """
    return {
        repo: data
        for repo, data in iter_openedx_yaml(hub, orgs=['edx', 'edx-ops', 'edx-solutions'])
        if data.get('openedx-release')
    }


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


def commit_ref_info(repos, hub, skip_invalid=False):
    """
    Returns a dictionary of information about what commit should be tagged
    for each repository passed into this function. The return type is as
    follows:

    {
        Repository(<full_repo_name>): {
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
        Repository(<next_repo_name>): {...}
    }

    If the information in the passed-in dictionary is invalid in any way,
    this function will throw an error unless `skip_invalid` is set to True,
    in which case the invalid information will simply be logged and ignored.
    """

    repos_by_name = {
        repo.full_name: repo_info
        for repo, repo_info
        in repos.items()
    }

    ref_info = {}
    for repo, repo_data in repos.items():
        # are we specifying a ref?
        ref = repo_data["openedx-release"].get("ref")
        if ref:
            try:
                ref_info[repo] = get_latest_commit_for_ref(
                    repo,
                    ref,
                )
            except (GitHubError, ValueError):
                if skip_invalid:
                    msg = "Invalid ref {ref} in repo {repo}".format(
                        ref=ref,
                        repo=repo.full_name
                    )
                    log.error(msg)
                    continue
                else:
                    raise
        # are we specifying a parent repo?
        parent_repo_name = repo_data["openedx-release"].get("parent-repo")
        if parent_repo_name:
            # we need the ref for the parent repo
            parent_release_data = repos_by_name[parent_repo_name]["openedx-release"]
            parent_ref = parent_release_data["ref"]
            requirements_file = parent_release_data.get("requirements", "requirements.txt")

            try:
                ref_info[repo] = get_latest_commit_for_parent_repo(
                    hub,
                    repo,
                    parent_repo_name,
                    parent_ref,
                    requirements_file,
                )
            except (GitHubError, ValueError):
                if skip_invalid:
                    msg = "Problem getting parent ref for repo {repo}".format(
                        repo=repo.full_name,
                    )
                    log.error(msg)
                    continue
                else:
                    raise
    return ref_info


def get_latest_commit_for_ref(repo, ref):
    """
    Given a repo name and a ref in that repo, return some information about
    the commit that the ref refers to. This function is called by
    commit_ref_info(), and it returns information in the same structure.
    """
    # is it a branch?
    branch = repo.branch(ref)
    if branch:
        commit = branch.commit.commit
        return {
            "ref": ref,
            "ref_type": "branch",
            "sha": branch.commit.sha,
            "message": commit.message,
            "author": commit.author,
            "committer": commit.committer,
        }

    tag = repo.ref('tags/{}'.format(ref))
    if tag:
        if tag.object.type == "tag":
            # An annotated tag, one more level of indirection.
            tag = repo.tag(tag.object.sha)
        # need to do a subsequent API call to get the tagged commit
        commit = repo.commit(tag.object.sha)
        if commit:
            return {
                "ref": ref,
                "ref_type": "tag",
                "sha": commit.sha,
                "message": commit.commit.message,
                "author": commit.commit.author,
                "committer": commit.commit.committer,
            }

    msg = "No commit for {ref} in {repo}".format(
        ref=ref, repo=repo.full_name,
    )
    raise ValueError(msg)


def get_latest_commit_for_parent_repo(
        hub, repo, parent_repo_name, parent_ref, requirements_file,
    ):
    """
    Some repos point to other repos via requirements files. For example,
    edx/edx-platform points to edx/XBlock and edx/edx-ora2 via the github.txt
    requirement file. This function takes two repo names: the target, and the
    target's parent. (In this case, "edx/XBlock" could be the target, and
    "edx/edx-platform" would be its parent.) This function looks up what
    reference the parent uses to point at the target, and looks up the commit
    that the reference points to in the target repo.

    This function is called by commit_ref_info(),
    and it returns information in the same structure.
    """

    file_contents = hub.repository(
        *parent_repo_name.split('/')
    ).contents(requirements_file, ref=parent_ref)

    ref = get_ref_for_dependency(
        file_contents.decoded,
        repo.full_name,
        parent_repo_name
    )

    return get_latest_commit_for_ref(repo, ref)


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


def get_ref_for_repos(repos, ref, use_tag=True):
    """
    Returns a dictionary with a key-value pairing for each repo in the given
    list of repos where the given ref exists in that repo. The key is the
    full name of the repo, and the value is a dictionary of information about
    the commit that the ref points to in that repo.
    If no repos contain the given ref, this function will return an empty dict
    -- as a result, you can use the return value of this function to check
    if the ref exists in any repos, just by coercing the return value
    to a boolean. (Empty dicts are falsy, populated dicts are truthy.)
    """
    if not ref.startswith("refs/"):
        ref = "refs/{type}/{name}".format(
            type="tags" if use_tag else "heads",
            name=ref,
        )
    return_value = {}
    for repo in repos:
        try:
            ref_obj = repo.ref(ref)
            found = ref_obj is not None
        except TypeError:
            # If the ref isn't found, GitHub uses the ref as a substring,
            # and returns all the refs that start with that string as an
            # array. That causes github3 to throw a type error when it
            # tries to pop a dict key from a list
            found = False

        if found:
            if ref_obj.object.type == "tag":
                # this is an annotated tag -- fetch the actual commit
                ref_obj = repo.tag(ref_obj.object.sha)
            commit = repo.commit(ref_obj.object.sha)

            # save the sha value for the commit into the returned dict
            return_value[repo.full_name] = {
                "ref": ref,
                "ref_type": ref_obj.type,
                "sha": commit.commit.sha,
                "message": commit.commit.message,
                "author": commit.commit.author,
                "committer": commit.commit.committer,
            }

    return return_value


def todo_list(ref_info):
    """
    Returns a string, suitable to be printed on the command line,
    that contains a record of the repos and commits that are about to be modified.
    If no ref info is passed in, return None.
    """
    if not ref_info:
        return None

    lines = []
    for repo_name, commit_info in ref_info.items():
        lines.append("{repo}: {ref} ({type}) {sha}".format(
            repo=repo_name,
            ref=commit_info['ref'],
            type=commit_info['ref_type'],
            sha=commit_info['sha'][0:7],
        ))
        when = datetime.datetime.strptime(commit_info['committer']['date'], "%Y-%m-%dT%H:%M:%SZ")
        lines.append("  {when:%Y-%m-%d} {who}: {msg}".format(
            msg=commit_info["message"].splitlines()[0],
            when=when,
            who=commit_info['committer']['name'],
        ))
    return "\n".join(lines)


def create_ref_for_repos(ref_info, ref, use_tag=True, rollback_on_fail=True, dry=True):
    """
    Actually create refs on the given repos.
    If `rollback_on_fail` is True, then on any failure, try to delete the refs
    that we're just created, so that we don't fail in a partially-completed
    state. (Note that this is *not* a reliable rollback -- other people could
    have already fetched the refs from GitHub, or the deletion attempt might
    itself fail!)

    If this function succeeds, it will return True. If this function fails,
    but the world is in a consistent state, this function will return False.
    The world is consistent if *no* refs were successfully created on repos in the first
    place, or all created refs were were successfully rolled
    back (because `rollback_on_fail` is set to True). If this function fails,
    and the world is in an inconsistent state, this function will raise a
    RuntimeError. This could happen if some (but not all) of the refs are created,
    and either rollback is not attempted (because `rollback_on_fail` is set to
    False), or rollback fails.
    """
    if not ref.startswith("refs/"):
        ref = "refs/{type}/{name}".format(
            type="tags" if use_tag else "heads",
            name=ref,
        )
    succeeded = []
    failed_resp = None
    failed_repo = None
    for repo, commit_info in ref_info.items():
        try:
            dry_echo(
                dry,
                'Creating ref {} with sha {} in repo {}'.format(
                    ref, commit_info['sha'], repo.full_name
                ),
                fg='green'
            )
            if not dry:
                created_ref = repo.create_ref(ref=ref, sha=commit_info['sha'])
                succeeded.append((repo, created_ref))
        except GitHubError as exc:
            failed_resp = exc.response
            failed_repo = repo
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
            "Failed to create {ref} on {failed_repo}. "
            "Error was {orig_err}. No refs have been created on any repos."
        ).format(
            ref=ref,
            failed_repo=failed_repo.full_name,
            orig_err=original_err_msg,
        )
        log.error(msg)
        return False

    if rollback_on_fail:
        rollback_failures = []
        for repo, created_ref in succeeded:
            try:
                dry_echo(
                    dry,
                    'Deleting ref {} from repo {}'.format(
                        created_ref.ref, repo.full_name
                    ),
                    fg='red'
                )
                if not dry:
                    created_ref.delete()
            except GitHubError as exc:
                rollback_failures.append(repo.full_name)

        if rollback_failures:
            msg = (
                "Failed to create {ref} on {failed_repo}. "
                "Error was {orig_err}. "
                "Attempted to roll back, but failed to delete ref on "
                "the following repos: {rollback_failures}"
            ).format(
                ref=ref,
                failed_repo=failed_repo.full_name,
                orig_err=original_err_msg,
                rollback_failures=", ".join(rollback_failures)
            )
            err = RuntimeError(msg)
            err.response = failed_resp
            err.repos = rollback_failures
            raise err
        else:
            msg = (
                "Failed to create {ref} on {failed_repo}. "
                "Error was {orig_err}. However, all refs were successfully "
                "rolled back."
            ).format(
                ref=ref,
                failed_repo=failed_repo.full_name,
                orig_err=original_err_msg,
            )
            log.error(msg)
            return False
    else:
        # don't try to rollback, just raise an error
        msg = (
            "Failed to create {ref} on {failed_repo}. "
            "Error was {orig_err}. No rollback attempted. Refs exist on "
            "the following repos: {tagged_repos}"
        ).format(
            ref=ref,
            failed_repo=failed_repo.full_name,
            orig_err=original_err_msg,
            tagged_repos=", ".join(repo.full_name for repo, _ in succeeded)
        )
        err = RuntimeError(msg)
        err.response = failed_resp
        err.repos = succeeded
        raise err


def remove_ref_for_repos(repos, ref, use_tag=True, dry=True):
    """
    Given an iterable of repository full names (like "edx/edx-platform") and
    a tag name, this function attempts to delete the named ref from each
    GitHub repository listed in the iterable. If the ref does not exist on
    the repo, it is skipped.

    This function returns True if any repos had the reference removed,
    or False if no repos were modified. If an error occurs while trying
    to remove a ref from a repo, the function will continue trying to
    remove refs from all the other repos in the iterable -- but after all repos
    have been attempted, this function will raise a RuntimeError with
    a list of all the repos that did not have the ref removed.
    Trying to remove a ref from a repo that does not have that ref
    to begin with is *not* treated as an error.
    """
    if ref.startswith('refs/'):
        ref = ref[len('refs/'):]

    if not (ref.startswith("heads/") or ref.startswith('tags/')):
        ref = "{type}/{name}".format(
            type="tags" if use_tag else "heads",
            name=ref,
        )

    failures = {}
    modified = False
    for repo in repos:
        try:
            ref_obj = repo.ref(ref)
            if ref_obj is None:
                # tag didn't exist to begin with; not an error
                continue

            dry_echo(
                dry,
                'Deleting ref {} from repo {}'.format(
                    ref_obj.ref, repo.full_name
                ),
                fg='red'
            )
            if not dry:
                ref_obj.delete()
            modified = True
        except GitHubError as err:
            # Oops, we got a failure. Record it and move on.
            failures[repo.full_name] = err

    if failures:
        msg = (
            "Failed to remove the ref from the following repos: {repos}"
        ).format(
            repos=", ".join(failures.keys())
        )
        err = RuntimeError(msg)
        err.failures = failures
        raise err

    return modified


@click.command()
@click.argument(
    'ref', metavar="REF",
)
@click.option(
    '--tag/--branch', "use_tag", is_flag=True,
    help="Whether to create branches or tags in the repo"
)
@click.option(
    '--override-ref', metavar="REF",
    help="A reference to use that overrides the references from the "
         "repos.yaml file in *ALL* repos. This might be a release candidate "
         "branch, for example."
)
@click.option(
    '--override', 'overrides',
    nargs=2, metavar="REPO REF",
    multiple=True,
    help="Override a reference for a specific repo. The repo must be "
         "specified using the full name of the repo, like 'edx/edx-platform'. "
         "This option can be provided multiple times."
)
@click.option(
    '-y', '--yes', 'interactive', is_flag=True, default=True,
    help="non-interactive mode: answer yes to all questions"
)
@click.option(
    '-q', '--quiet', is_flag=True, default=False,
    help="don't print any unnecessary output"
)
@click.option(
    '-R', '--reverse', is_flag=True, default=False,
    help="delete ref instead of creating it"
)
@click.option(
    '--skip-invalid', is_flag=True, default=False,
    help="if the repos.yaml file points to an invalid repo, skip it "
         "instead of throwing an error"
)
@dry
@pass_github
def main(hub, ref, use_tag, override_ref, overrides, interactive, quiet, reverse, skip_invalid, dry):
    """Create/remove tags & branches on GitHub repos for Open edX releases."""

    repos = openedx_release_repos(hub)
    if not repos:
        raise ValueError("No repos marked for openedx-release in repos.yaml!")

    repos = override_repo_refs(
        repos,
        override_ref=override_ref,
        overrides=dict(overrides or ()),
    )

    existing_refs = get_ref_for_repos(repos, ref, use_tag=use_tag)

    if reverse:
        if not existing_refs:
            msg = (
                "Ref {ref} is not present in any repos, cannot remove it"
            ).format(
                ref=ref,
            )
            print(msg)
            return False
        if interactive or not quiet:
            print(todo_list(existing_refs))
        if interactive:
            response = raw_input("Remove these refs? [y/N] ")
            if response.lower() not in ("y", "yes", "1"):
                return

        modified = remove_ref_for_repos(repos, ref, use_tag=use_tag, dry=dry)
        if not quiet:
            if modified:
                print("Success!")
            else:
                print("No refs modified")
        return modified

    else:
        if existing_refs:
            msg = (
                "The {ref} ref already exists in the following repos: {repos}"
            ).format(
                ref=ref,
                repos=", ".join(existing_refs.keys()),
            )
            raise ValueError(msg)

        ref_info = commit_ref_info(repos, hub, skip_invalid=skip_invalid)
        if interactive or not quiet:
            print(todo_list(ref_info))
        if interactive:
            response = raw_input("Is this correct? [y/N] ")
            if response.lower() not in ("y", "yes", "1"):
                return

        result = create_ref_for_repos(ref_info, ref, use_tag=use_tag, dry=dry)
        if not quiet:
            if result:
                print("Success!")
            else:
                print("Failed to create refs, but rolled back successfully")
        return result
