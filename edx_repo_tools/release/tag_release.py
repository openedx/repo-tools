#!/usr/bin/env python
"""
Tag repos for an Open edX release. When run, this script will:

1. Make sure we have an OAuth token for the GitHub API, and help the user
   create one if we don't already have one
2. Fetch the openedx.yaml files from all repos covered by the Open edX release.
3. Identify the repos in that file that are tagged in the Open edX release
4. Identify the commit that needs to be tagged in each repo, tracing cross-repo
   dependencies as necessary
5. Show the identified repos and commits, and ask for confirmation from the user
6. Upon confirmation, create Git tags for the repos using the GitHub API
"""

import collections
import copy
import datetime
import logging

import click
from edx_repo_tools.auth import pass_github
from edx_repo_tools.data import iter_openedx_yaml
from edx_repo_tools.utils import dry, dry_echo
from github3 import GitHubError

log = logging.getLogger(__name__)


# Name used for fetching/storing GitHub OAuth tokens on disk
TOKEN_NAME = "openedx-release"


# An object to act like a response (with a .text attribute) in the case that
# create_ref uselessly returns us None on failure.
FakeResponse = collections.namedtuple("FakeResponse", "text")


def openedx_release_repos(hub, orgs=None, branches=None):
    """
    Return a subset of the repos with openedx.yaml files: the repos
    with an `openedx-release` section.


    Arguments:
        hub (GitHub): an authenticated GitHub instance.
        orgs: The list of GitHub orgs to scan. Defaults to edx, edx-ops, and
              edx-solutions.
        branches: The list of branches to scan in all repos in the selected
                  orgs.

    Returns:
        A dict from Repository objects to openedx.yaml data for all of the
        repos with an ``openedx-release`` key specified.
    """
    if not orgs:
        orgs = ['edx', 'edx-ops', 'edx-solutions']

    return {
        repo: data
        for repo, data in iter_openedx_yaml(
            hub,
            orgs=orgs,
            branches=branches,
        )
        if data.get('openedx-release')
    }


def trim_skipped_repos(repos, skip_repos):
    """Remove repos we've been told to skip."""
    trimmed = {}
    for r, data in repos.items():
        if any((r.full_name == sr or r.name == sr) for sr in skip_repos):
            continue
        trimmed[r] = data
    return trimmed

def trim_dependent_repos(repos):
    """Remove dependent repos (an obsolete feature of this program).

    Repos with 'parent-repo' in their 'openedx-release' data are removed from
    the `repos` dict.  A new dict of repos is returned.

    """
    trimmed = {}

    for r, data in repos.items():
        if 'parent-repo' in data['openedx-release']:
            msg = u"Repo {repo} is dependent: you can remove openedx-release from its openedx.yaml file".format(repo=r)
            click.secho(msg, fg='yellow')
        else:
            trimmed[r] = data

    return trimmed


def override_repo_refs(repos, override_ref=None, overrides=None):
    """
    Returns a new `repos` dictionary with the CLI overrides applied.
    """
    overrides = overrides or {}
    if not override_ref and not overrides:
        return repos

    repos_copy = copy.deepcopy(repos)
    for repo, repo_data in repos.items():
        if not repo_data:
            continue
        release_data = repo_data.get("openedx-release")
        if not release_data:
            continue
        local_override = overrides.get(str(repo), override_ref)
        if local_override:
            repos_copy[repo]["openedx-release"]["ref"] = local_override

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
                    msg = u"Invalid ref {ref} in repo {repo}".format(
                        ref=ref,
                        repo=repo.full_name
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

    try:
        tag = repo.ref('tags/{}'.format(ref))
    except TypeError as err:
        # GitHub unfortunately returns a list of partial matches if you ask for
        # a ref that doesn't exist.  This means the code in github3 that
        # expects a dict (the ref that matches) actually gets a list instead.
        # Then it tries to pop, and a TypeError occurs
        # https://github.com/sigmavirus24/github3.py/issues/310
        # We'll catch the error and make the problem clearer.
        if "pop() takes at most 1 argument (2 given)" in str(err):
            raise Exception("In repo {}, ref {!r} doesn't exist.".format(repo, ref))
        else:
            raise
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

    # Github3's repo.ref function wants a ref without a leading "refs/", even
    # though the create_ref function wants one *with* a leading "refs/". :(
    if ref.startswith("refs/"):
        ref = ref[5:]
    elif not ref.startswith(("heads", "tags")):
        ref = "{type}/{name}".format(
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
                "ref": "refs/" + ref,
                "ref_type": "tag" if use_tag else "branch",
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

    entries = []
    for repo, commit_info in ref_info.items():
        when = datetime.datetime.strptime(commit_info['committer']['date'], "%Y-%m-%dT%H:%M:%SZ")
        entries.append(u"{repo}: {ref} ({type}) {sha}\n  {when:%Y-%m-%d} {who}: {msg}".format(
            repo=repo,
            ref=commit_info['ref'],
            type=commit_info['ref_type'],
            sha=commit_info['sha'][0:7],
            msg=commit_info["message"].splitlines()[0],
            when=when,
            who=commit_info['committer']['name'],
        ))
    return "\n".join(sorted(entries))


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
        ref = u"refs/{type}/{name}".format(
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
                u'Creating ref {} with sha {} in repo {}'.format(
                    ref, commit_info['sha'], repo.full_name
                ),
                fg='green'
            )
            if not dry:
                created_ref = repo.create_ref(ref=ref, sha=commit_info['sha'])
                if created_ref is None:
                    failed_resp = FakeResponse(text="Something went terribly wrong, not sure what")
                    failed_repo = repo
                    break
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
            u"Failed to create {ref} on {failed_repo}. "
            u"Error was {orig_err}. No refs have been created on any repos."
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
                    u'Deleting ref {} from repo {}'.format(
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
                u"Failed to create {ref} on {failed_repo}. "
                u"Error was {orig_err}. "
                u"Attempted to roll back, but failed to delete ref on "
                u"the following repos: {rollback_failures}"
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
                u"Failed to create {ref} on {failed_repo}. "
                u"Error was {orig_err}. However, all refs were successfully "
                u"rolled back."
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
            u"Failed to create {ref} on {failed_repo}. "
            u"Error was {orig_err}. No rollback attempted. Refs exist on "
            u"the following repos: {tagged_repos}"
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
                u'Deleting ref {} from repo {}'.format(
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
            u"Failed to remove the ref from the following repos: {repos}"
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
    '--tag/--branch', "use_tag", is_flag=True, default=True,
    help=u"Whether to create branches or tags in the repo. Defaults to using tags."
)
@click.option(
    '--override-ref', metavar="REF",
    help=u"A reference to use that overrides the references from the "
         u"openedx.yaml file in *ALL* repos. This might be a release candidate "
         u"branch, for example."
)
@click.option(
    '--override', 'overrides',
    nargs=2, metavar="REPO REF",
    multiple=True,
    help=u"Override a reference for a specific repo. The repo must be "
         u"specified using the full name of the repo, like 'edx/edx-platform'. "
         u"This option can be provided multiple times."
)
@click.option(
    '-y', '--yes', 'interactive', is_flag=True, default=True, flag_value=False,
    help=u"non-interactive mode: answer yes to all questions"
)
@click.option(
    '-q', '--quiet', is_flag=True, default=False,
    help=u"don't print any unnecessary output"
)
@click.option(
    '-R', '--reverse', is_flag=True, default=False,
    help=u"delete ref instead of creating it"
)
@click.option(
    '--skip-invalid', is_flag=True, default=False,
    help=u"if the openedx.yaml file points to an invalid repo, skip it "
         u"instead of throwing an error"
)
@click.option(
    '--skip-repo', 'skip_repos', multiple=True,
    help="Specify repos that should be ignored in spite of having an openedx.yaml file."
)
@click.option(
    '--search-branch', 'branches', multiple=True,
    help="Specify a branch to search for the openedx.yaml file. If specified "
         "multiple times, the first openedx.yaml file found will be used.",
)
@click.option(
    '--org', 'orgs', multiple=True, default=['edx', 'edx-ops', 'edx-solutions'],
    help="Specify a GitHub organization to search for openedx release data. "
         "May be specified multiple times.",
)
@dry
@pass_github
def main(hub, ref, use_tag, override_ref, overrides, interactive, quiet,
         reverse, skip_invalid, skip_repos, dry, orgs, branches):
    """Create/remove tags & branches on GitHub repos for Open edX releases."""

    repos = openedx_release_repos(hub, orgs, branches)
    if not repos:
        raise ValueError(u"No repos marked for openedx-release in their openedx.yaml files!")

    repos = trim_skipped_repos(repos, skip_repos)
    repos = trim_dependent_repos(repos)

    repos = override_repo_refs(
        repos,
        override_ref=override_ref,
        overrides=dict(overrides or ()),
    )

    existing_refs = get_ref_for_repos(repos, ref, use_tag=use_tag)

    if reverse:
        if not existing_refs:
            msg = (
                u"Ref {ref} is not present in any repos, cannot remove it"
            ).format(
                ref=ref,
            )
            click.echo(msg)
            return False
        if interactive or not quiet:
            click.echo(todo_list(existing_refs))
        if interactive:
            if not click.confirm(u"Remove these refs?"):
                return

        modified = remove_ref_for_repos(repos, ref, use_tag=use_tag, dry=dry)
        if not quiet:
            if modified:
                click.echo(u"Success!")
            else:
                click.echo(u"No refs modified")
        return modified

    else:
        if existing_refs:
            msg = (
                u"The {ref} ref already exists in the following repos: {repos}"
            ).format(
                ref=ref,
                repos=", ".join(existing_refs.keys()),
            )
            raise ValueError(msg)

        ref_info = commit_ref_info(repos, hub, skip_invalid=skip_invalid)
        if interactive or not quiet:
            click.echo(todo_list(ref_info))
        if interactive:
            if not click.confirm(u"Is this correct?"):
                return
        result = create_ref_for_repos(ref_info, ref, use_tag=use_tag, dry=dry)

        if not quiet:
            if result:
                click.echo(u"Success!")
            else:
                raise ValueError(u"Failed to create refs, but rolled back successfully")
        return result
