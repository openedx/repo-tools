# pylint: disable=too-many-lines
# pylint: disable=f-string-without-interpolation
"""
Run checks against repos and correct them if they're missing something.

See README.rst in this directory for details.

This script was originally developed in the terraform-github repository.
If you're trying to git-blame it, you might need to dig into the original source:
https://github.com/openedx-unsupported/terraform-github/blame/main/migrate/repo_checks.py
"""
from __future__ import annotations

import importlib.resources
import re
import textwrap
import typing as t
from functools import cache
from itertools import chain
from pprint import pformat

import click
import requests
import yaml

# Pylint doesn't believe that fastcore.net exports these error classes...
# pylint: disable=no-name-in-module
from fastcore.net import (
    HTTP4xxClientError,
    HTTP404NotFoundError,
    HTTP409ConflictError,
)

# pylint: enable=no-name-in-module
from ghapi.all import GhApi, paged

HAS_GHSA_SUFFIX = re.compile(r".*?-ghsa-\w{4}-\w{4}-\w{4}$")

LABELS_YAML_FILENAME = "./labels.yaml"


def all_paged_items(func, *args, **kwargs):
    """
    Get all items from a GhApi function returning paged results.
    """
    return chain.from_iterable(paged(func, *args, per_page=100, **kwargs))


def is_security_private_fork(api, org, repo):
    """
    Check to see if a specific repo is a private security fork.
    """

    # Also make sure that it's a private repo.
    is_private = api.repos.get(org, repo).private

    return is_private and HAS_GHSA_SUFFIX.match(repo)


def is_public(api, org, repo):
    """
    Check to see if a specific repo is public.
    """

    is_private = api.repos.get(org, repo).private

    return not is_private


def is_empty(api, org, repo):
    """
    Check to see if a specific repo is empty and has no commits yet.
    """
    default_branch = api.repos.get(org, repo).default_branch

    try:
        _default_branch_ref = api.git.get_ref(
            org,
            repo,
            f"heads/{default_branch}",
        )
    except HTTP409ConflictError as err:
        if "Git Repository is empty." in str(err):
            return True
        raise
    return False


@cache
def get_github_file_contents(api, org, repo, path, ref):
    """
    A caching proxy for the get repository content api endpoint.

    It returns the content of the file as a string.
    """
    return api.repos.get_content(org, repo, path, ref).content


class Check:
    """
    Something that we want to ensure about a given repository.

    This is an abstract class; concrete checks should be implemented
    as subclasses and override the four methods below
    (is_relevant, check, fix, and dry_run).
    """

    _registered = {}

    def __init__(self, api: GhApi, org: str, repo: str):
        self.api = api
        self.org_name = org
        self.repo_name = repo

    @staticmethod
    def register(subclass: type[t.Self]) -> type[t.Self]:
        """
        Decorate a Check subclass so that it will be available in main()
        """
        Check._registered[subclass.__name__] = subclass
        return subclass

    @staticmethod
    def get_registered_checks() -> dict[str, type[t.Self]]:
        return Check._registered.copy()

    def is_relevant(self) -> bool:
        """
        Checks to see if the given check is relevant to run on the
        given repo.

        This is independent of whether or not the check passes on this repo
        and should be run before trying to check the repo.
        """

        raise NotImplementedError

    def check(self) -> tuple[bool, str]:
        """
        Verify whether or not the check is failing.

        This should not change anything and should not have a side-effect
        other than populating `self` with any data that is needed later for
        `fix` or `dry_run`.

        The string in the return tuple should be a human readable reason
        that the check failed.
        """

        raise NotImplementedError

    def fix(self):
        """
        Make an idempotent change to resolve the issue.

        Expects that `check` has already been run.
        """

        raise NotImplementedError

    def dry_run(self):
        """
        See what will happen without making any changes.

        Expects that `check` has already been run.
        """
        raise NotImplementedError


@Check.register
class Settings(Check):
    """
    There are certain settings that we agree we want to be set a specific way on all repos.  This check
    will ensure that those settings are set correctly on all non-security repos.

    Settings:
    - Issues should be enabled.
    - Wikis should be disabled.  The confluence wiki should be used.
    - Allow auto-merge to be used. (Does not enable auto-merge, just allows committers to enable it on a per PR basis.)
    - Branches should be deleted on merge.
    """

    def __init__(self, api: GhApi, org: str, repo: str):
        super().__init__(api, org, repo)
        self.expected_settings = {
            "has_issues": True,
            "has_wiki": False,
            "allow_auto_merge": True,
            "delete_branch_on_merge": True,
        }

    def is_relevant(self) -> bool:
        """
        All non security fork repos, public or private.
        """
        return not is_security_private_fork(self.api, self.org_name, self.repo_name)

    def check(self) -> tuple[bool, str]:
        """
        Verify whether or not the check is failing.

        This should not change anything and should not have a side-effect
        other than populating `self` with any data that is needed later for
        `fix` or `dry_run`.

        The string in the return tuple should be a human readable reason
        that the check failed.
        """
        repo = self.api.repos.get(owner=self.org_name, repo=self.repo_name)

        self.settings_that_dont_match = []
        for setting in self.expected_settings:
            actual_value = repo.get(setting)
            if actual_value != self.expected_settings[setting]:
                self.settings_that_dont_match.append((setting, actual_value))

        if self.settings_that_dont_match:
            # Looks like this:
            #     Some settings don't match our expectations:
            #             allow_auto_merge: False
            #             delete_branch_on_merge: False
            return (
                False,
                f"Some settings don't match our expectations:\n\t\t"
                + "\n\t\t".join(
                    [
                        f"{setting[0]}: {setting[1]}"
                        for setting in self.settings_that_dont_match
                    ]
                ),
            )

        return (True, "All expected settings are set correctly.")

    def dry_run(self):
        return self.fix(dry_run=True)

    def fix(self, dry_run=False):
        steps = []
        if self.settings_that_dont_match:
            if not dry_run:
                self.api.repos.update(
                    self.org_name, self.repo_name, **self.expected_settings
                )
            steps.append(
                f"Updated repo settings to match expectations.\n\t"
                + "\n\t".join(
                    [
                        f"{setting[0]}: {self.expected_settings[setting[0]]}"
                        for setting in self.settings_that_dont_match
                    ]
                )
            )
        else:
            steps.append("No changes needed.")
        return steps


@Check.register
class NoAdminOrMaintainTeams(Check):
    """
    Teams should not be granted `admin` or `maintain` access to a repository unless the access
    is exceptional and it is noted here.  All other `admin` and `maintain` access is downgraded to
    `write` access.
    """

    def __init__(self, api: GhApi, org: str, repo: str):
        super().__init__(api, org, repo)
        self.teams_to_downgrade = []

    def is_relevant(self) -> bool:
        """
        All non security fork repos, public or private.
        """
        return not is_security_private_fork(self.api, self.org_name, self.repo_name)

    def check(self) -> tuple[bool, str]:
        """
        Verify whether or not the check is failing.

        This should not change anything and should not have a side-effect
        other than populating `self` with any data that is needed later for
        `fix` or `dry_run`.

        The string in the return tuple should be a human readable reason
        that the check failed.
        """
        teams = all_paged_items(
            self.api.repos.list_teams, owner=self.org_name, repo=self.repo_name
        )
        for team in teams:
            if team.permission in ["admin", "maintain"]:
                self.teams_to_downgrade.append(team)

        if self.teams_to_downgrade:
            team_and_permissions = list(
                {f"{team.slug}: {team.permission}" for team in self.teams_to_downgrade}
            )
            return (
                False,
                f"Some teams have excessive permissions:\n\t\t"
                + "\n\t\t".join(team_and_permissions),
            )

        return (True, "No teams with `admin` or `maintain` permissions.")

    def dry_run(self):
        return self.fix(dry_run=True)

    def fix(self, dry_run=False):
        steps = []
        for team in self.teams_to_downgrade:
            if not dry_run:
                self.api.teams.add_or_update_repo_permissions_in_org(
                    self.org_name,
                    team.slug,
                    self.org_name,
                    self.repo_name,
                    "push",
                )

            steps.append(
                f"Reduced permission of `{team.slug}` from `{team.permission}` to `push`"
            )

        return steps


@Check.register
class Workflows(Check):
    """
    There are certain github action workflows that we to exist on all
    repos exactly as they are defined in the `.github` repo in the org.

    Check to see if they're in a repo and if not, make a pull request
    to add them to the repository.
    """

    def __init__(self, api: GhApi, org: str, repo: str):
        super().__init__(api, org, repo)

        self.workflow_templates = [
            "self-assign-issue.yml",
            "add-depr-ticket-to-depr-board.yml",
            "commitlint.yml",
            "add-remove-label-on-comment.yml",
        ]

        # A lost of repos and workflows that should not be added to them.
        self.exceptions = {
            # We don't want commitlint on the docs.openedx.org and edx-documentation repos because
            # we want to encourage contributions from non-technical contributors and reduce their
            # barrier to entry.
            "docs.openedx.org": ["commitlint.yml"],
            "edx-documentation": ["commitlint.yml"],
        }

        self.branch_name = "repo_checks/ensure_workflows"

        self.files_to_create = []
        self.files_to_update = []
        self.dot_github_template_contents = {}

    def is_relevant(self):
        return (
            is_public(self.api, self.org_name, self.repo_name)
            and not is_empty(self.api, self.org_name, self.repo_name)
            and self.repo_name != ".github"
        )

    def check(self):
        """
        See if our workflow templates are in the repo and have the same content
        as the default templates in the `.github` repo.
        """
        # Get the current default branch.
        repo = self.api.repos.get(self.org_name, self.repo_name)
        default_branch = repo.default_branch

        files_that_differ, files_that_are_missing = self._check_branch(default_branch)

        extra_message = "No repo specific workflows to ignore."
        # Update based on repo specific exceptions
        if self.repo_name in self.exceptions:
            extra_message = (
                "Ignoring repo specific exceptions: {!r}".format(
                    self.exceptions[self.repo_name]
                )
            )
            # We have exceptions for this repo, remove them from the two lists above.
            for item in self.exceptions[self.repo_name]:
                if item in files_that_differ:
                    files_that_differ.remove(item)
                if item in files_that_are_missing:
                    files_that_are_missing.remove(item)

        # Return False and save the list of files that need to be updated.
        if files_that_differ or files_that_are_missing:
            self.files_to_create = files_that_are_missing
            self.files_to_update = files_that_differ
            return (
                False,
                f"Some workflows in this repo don't match the template.\n"
                f"\t\t{files_that_differ=}\n\t\t{files_that_are_missing=}\n"
                f"\t\t{extra_message}",
            )

        return (
            True,
            "All desired workflows are in sync with what's in the .github repo.\n"
            f"\t\t{extra_message}",
        )

    def _check_branch(self, branch_name) -> tuple[list[str], list[str]]:
        """
        Check the contents the listed workflow files on a branch against the
        default content in the .github folder.
        """
        dot_github_default_branch = self.api.repos.get(
            self.org_name, ".github"
        ).default_branch
        # Get the content of the .github files, maybe this should be a memoized
        # function since we'll want to get the same .github content from all
        # the repos.
        for file in self.workflow_templates:
            file_path = f"workflow-templates/{file}"
            try:
                self.dot_github_template_contents[file] = get_github_file_contents(
                    self.api,
                    self.org_name,
                    ".github",
                    file_path,
                    dot_github_default_branch,
                )
            except HTTP4xxClientError as err:
                click.echo(
                    f"File: https://github.com/{self.org_name}/"
                    f".github/blob/{dot_github_default_branch}/{file_path}"
                )
                click.echo(err.fp.read().decode("utf-8"))
                raise

        # Get the content of the repo specific file.
        repo_contents = {}
        files_that_are_missing = []
        for file in self.workflow_templates:
            file_path = f".github/workflows/{file}"
            try:
                repo_contents[file] = get_github_file_contents(
                    self.api,
                    self.org_name,
                    self.repo_name,
                    file_path,
                    branch_name,
                )
            except HTTP4xxClientError as err:
                if err.status == 404:
                    files_that_are_missing.append(file)

        # Compare the two.
        files_that_differ = []
        for file in self.workflow_templates:
            if (
                file not in files_that_are_missing
                and self.dot_github_template_contents[file] != repo_contents[file]
            ):
                files_that_differ.append(file)

        return (files_that_differ, files_that_are_missing)

    def dry_run(self):
        return self.fix(dry_run=True)

    def fix(self, dry_run=False):
        """
        Always use the same branch name and update the contents if necessary.
        """
        steps = []
        if not (self.files_to_create or self.files_to_update):
            return steps

        # Check to see if the update branch already exists.
        branch_exists = True
        try:
            self.api.git.get_ref(
                self.org_name, self.repo_name, f"heads/{self.branch_name}"
            )
        except HTTP4xxClientError as err:
            if err.status == 404:
                branch_exists = False
            else:
                raise  # For any other unexpected errors.

        # Get the hash of the default branch.
        repo = self.api.repos.get(self.org_name, self.repo_name)
        default_branch = repo.default_branch
        default_branch_sha = self.api.git.get_ref(
            self.org_name,
            self.repo_name,
            f"heads/{default_branch}",
        ).object.sha

        if branch_exists:
            steps.append("Workflow branch already exists.  Updating branch.")

            if not dry_run:
                # Force-push the branch to the lastest sha of the default branch.
                self.api.git.update_ref(
                    self.org_name,
                    self.repo_name,
                    f"heads/{self.branch_name}",
                    default_branch_sha,
                    force=True,
                )

        else:  # The branch does not exist
            steps.append(f"Branch does not exist. Creating '{self.branch_name}'.")
            if not dry_run:
                self.api.git.create_ref(
                    self.org_name,
                    self.repo_name,
                    # The create api needs the `refs/` prefix while the get api doesn't,
                    # be sure to check the API reference before adding calls to other
                    # parts of the GitHub `git/refs` REST api.
                    # https://docs.github.com/en/rest/git/refs?apiVersion=2022-11-28
                    f"refs/heads/{self.branch_name}",
                    default_branch_sha,
                )

        steps.append(f"Updating workflow files on '{self.branch_name}'.")
        commit_message_template = textwrap.dedent(
            """
            build: {creating_or_updating} workflow `{workflow}`.

            The {path_in_repo} workflow is missing or needs an update to stay in
            sync with the current standard for this workflow as defined in the
            `.github` repo of the `{org_name}` GitHub org.
            """
        )

        for workflow in self.files_to_create + self.files_to_update:
            if workflow in self.files_to_create:
                creating_or_updating = "Creating"
            else:
                creating_or_updating = "Updating"

            path_in_repo = f".github/workflows/{workflow}"
            commit_message = commit_message_template.format(
                creating_or_updating=creating_or_updating,
                path_in_repo=path_in_repo,
                workflow=workflow,
                org_name=self.org_name,
            )
            file_content = self.dot_github_template_contents[workflow]

            steps.append(f"{creating_or_updating} {path_in_repo}")
            if not dry_run:
                # We need the sha to update an existing file.
                if workflow in self.files_to_create:
                    current_file_sha = None
                else:
                    current_file_sha = self.api.repos.get_content(
                        self.org_name,
                        self.repo_name,
                        path_in_repo,
                        self.branch_name,
                    ).sha

                self.api.repos.create_or_update_file_contents(
                    owner=self.org_name,
                    repo=self.repo_name,
                    path=path_in_repo,
                    message=commit_message,
                    content=file_content,
                    sha=current_file_sha,
                    branch=self.branch_name,
                )

        # Check to see if a PR exists
        prs = all_paged_items(
            self.api.pulls.list,
            owner=self.org_name,
            repo=self.repo_name,
            head=self.branch_name,
        )

        prs = [pr for pr in prs if pr.head.ref == self.branch_name]

        if prs:
            pr = prs[0]
            steps.append(f"PR already exists: {prs[0].html_url}")
        else:
            # If not, create a new PR
            steps.append("No PR exists, creating a PR.")
            pr_body = textwrap.dedent(
                """
                This PR was created automatically by [the `repo_checks` tool](https://github.com/openedx/repo-tools/tree/master/edx_repo_tools/repo_checks).
                """
            )
            if not dry_run:
                pr = self.api.pulls.create(
                    owner=self.org_name,
                    repo=self.repo_name,
                    title="Update standard workflow files.",
                    head=self.branch_name,
                    base=default_branch,
                    body=pr_body,
                    maintainer_can_modify=True,
                )
                steps.append(f"New PR: {pr.html_url}")

        return steps


@Check.register
class Labels(Check):
    """
    All repos in the org should have certain labels.
    """

    # Load up the labels file in the class definition so that we fail
    # fast if the file isn't valid YAML.
    # Each item should be a dict with the fields:
    #  name: str
    #  color: str (rrggbb hex string)
    #  description: str
    labels: list[dict[str, str]] = yaml.safe_load(
        importlib.resources.read_text(__package__, "labels.yaml")
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.missing_labels = []
        self.labels_that_need_updates = []  # pair of (current_label, new_label)

    def is_relevant(self):
        return not is_security_private_fork(self.api, self.org_name, self.repo_name)

    def check(self):
        """
        See if our labels exist.
        """
        existing_labels_from_api = all_paged_items(
            self.api.issues.list_labels_for_repo,
            self.org_name,
            self.repo_name,
        )
        existing_labels = {
            self._simplify_label(label.name): {
                "color": label.color,
                "name": label.name,
                "description": label.description,
            }
            for label in existing_labels_from_api
        }
        self.missing_labels = []
        self.labels_that_need_updates = []  # pair of (current_label, new_label)

        for new_label in self.labels:
            simple_name = self._simplify_label(new_label["name"])
            if simple_name in existing_labels:
                # We need to potentially update the label if the details have changed.
                if existing_labels[simple_name] != new_label:
                    self.labels_that_need_updates.append(
                        (existing_labels[simple_name], new_label)
                    )
            else:
                # We need to create the label as it doesn't already exist.
                self.missing_labels.append(new_label)

        if self.missing_labels or self.labels_that_need_updates:
            return (
                False,
                "Labels need updating. "
                f"{len(self.missing_labels)} to create, "
                f"{len(self.labels_that_need_updates)} to fix.",
            )
        return (
            True,
            "All desired labels exist with the right name, color, description.",
        )

    def dry_run(self):
        return self.fix(dry_run=True)

    def fix(self, dry_run=False):
        steps = []

        # Create missing labels
        for label in self.missing_labels:
            if not dry_run:
                try:
                    self.api.issues.create_label(
                        owner=self.org_name,
                        repo=self.repo_name,
                        name=label["name"],
                        color=label["color"],
                        description=label["description"],
                    )
                except HTTP4xxClientError as err:
                    click.echo(err.fp.read().decode("utf-8"))
                    raise
            steps.append(f"Created {label=}.")

        # Update labels with incorrect details
        for current_label, new_label in self.labels_that_need_updates:
            if not dry_run:
                try:
                    self.api.issues.update_label(
                        owner=self.org_name,
                        repo=self.repo_name,
                        name=current_label["name"],
                        color=new_label["color"],
                        description=new_label["description"],
                        new_name=new_label["name"],
                    )
                except HTTP4xxClientError as err:
                    click.echo(err.fp.read().decode("utf-8"))
                    raise
            steps.append(f"Fixed {current_label=} to {new_label=}")

        return steps

    def _simplify_label(self, label: str):
        special_content = re.compile(r"(:\S+:|-|_|'|\"|\.|\!|\s)")

        simplified_label = special_content.sub("", label).strip().lower()
        return simplified_label


class TeamAccess(Check):
    """
    Require that a team has a certain level of access to a repository.

    To use this class as a check, create a subclass that specifies a particular
    team and permission level, such as TriageTeam below.
    """

    def __init__(self, api: GhApi, org: str, repo: str, team: str, permission: str):
        """
        Valid permission strings are defined in the Github REST API docs:

        https://docs.github.com/en/rest/teams/teams#add-or-update-team-repository-permissions

        They include 'pull', 'triage', 'push', 'maintain', and 'admin'.
        """
        super().__init__(api, org, repo)
        self.team = team
        self.permission = permission

        self.team_setup_correctly = False

    def is_relevant(self):
        raise NotImplementedError

    def check(self):
        teams = all_paged_items(
            self.api.repos.list_teams,
            self.org_name,
            self.repo_name,
        )

        team_permissions = {team.slug: team.permission for team in teams}
        if self.team not in team_permissions:
            return (False, f"'{self.team}' team not listed on the repo.")
        # Check to see if the team has the correct permission.
        # More and less acess are both considered incorrect.
        if team_permissions[self.team] != self.permission:
            return (
                False,
                f"'{self.team}' team does not have the correct access. "
                f"Has {team_permissions[self.team]} instead of {self.permission}.",
            )
        self.team_setup_correctly = True
        return (True, f"'{self.team}' team has '{self.permission}' access.")

    def dry_run(self):
        """
        Provide info on what would be done to make this check pass.
        """
        return self.fix(dry_run=True)

    def fix(self, dry_run=False):
        if self.team_setup_correctly:
            return []

        try:
            if not dry_run:
                self.api.teams.add_or_update_repo_permissions_in_org(
                    self.org_name,
                    self.team,
                    self.org_name,
                    self.repo_name,
                    self.permission,
                )
            return [
                f"Added {self.permission} access for {self.team} to {self.repo_name}."
            ]
        except HTTP4xxClientError as err:
            click.echo(err.fp.read().decode("utf-8"))
            raise


@Check.register
class TriageTeam(TeamAccess):
    """
    Ensure that the openedx-triage team grants Triage access to every public repo in the org.
    """

    def __init__(self, api, org, repo):
        team = "openedx-triage"
        permission = "triage"
        super().__init__(api, org, repo, team, permission)

    def is_relevant(self):
        # Need to be a public repo.
        return is_public(self.api, self.org_name, self.repo_name)


@Check.register
class EnforceCLA(Check):
    """
    This class validates the following:

    * Branch Protection is enabled on the default branch.
    * The CLA Check is a required check.

    If the check fails, the fix function can update the repo
    so that it has branch protection enabled with the "openedx/cla"
    check as a required check.
    """

    def __init__(self, api, org, repo):
        super().__init__(api, org, repo)

        self.cla_check = {"context": "openedx/cla", "app_id": -1}

        self.cla_team = "cla-checker"
        self.cla_team_permission = "push"

        self.team_check = TeamAccess(
            api,
            org,
            repo,
            self.cla_team,
            self.cla_team_permission,
        )

        self.has_a_branch_protection_rule = False
        self.branch_protection_has_required_checks = False
        self.required_checks_has_cla_required = False
        self.team_setup_correctly = False

    def is_relevant(self):
        return not is_security_private_fork(self.api, self.org_name, self.repo_name)

    def check(self):
        is_required_check = self._check_cla_is_required_check()
        repo_on_required_team = self.team_check.check()

        value = is_required_check[0] and repo_on_required_team[0]
        reason = f"{is_required_check[1]} {repo_on_required_team[1]}"
        return (value, reason)

    def _check_cla_is_required_check(self) -> tuple[bool, str]:
        """
        Is the CLA required on the repo? If not, what's wrong?
        """
        repo = self.api.repos.get(self.org_name, self.repo_name)
        default_branch = repo.default_branch
        # Branch protection rule might not exist.
        try:
            branch_protection = self.api.repos.get_branch_protection(
                self.org_name, self.repo_name, default_branch
            )
            self.has_a_branch_protection_rule = True
        except HTTP404NotFoundError:
            return (False, "No branch protection rule.")

        if "required_status_checks" not in branch_protection:
            return (False, "No required status checks in place.")
        self.branch_protection_has_required_checks = True

        # We don't need to check the `contexts` list because, github mirrors
        # all existing checks in `contexts` into the `checks` data.  The `contexts`
        # data is deprecated and will not be available in the future.
        contexts = [
            check["context"]
            for check in branch_protection.required_status_checks.checks
        ]
        if "openedx/cla" not in contexts:
            return (False, "CLA Check is not a required check.")
        self.required_checks_has_cla_required = True

        return (True, "Branch Protection with CLA Check is in Place.")

    def dry_run(self):
        """
        Provide info on what would be done to make this check pass.
        """
        return self.fix(dry_run=True)

    def fix(self, dry_run=False):
        steps = []
        if not self.required_checks_has_cla_required:
            steps += self._fix_branch_protection(dry_run)

        if not self.team_check.team_setup_correctly:
            steps += self.team_check.fix(dry_run)

        return steps

    def _fix_branch_protection(self, dry_run=False):
        """
        Ensure the default branch is has a protection which requires the CLA check.
        """
        try:
            steps = []

            # Short Circuit if there is nothing to do.
            if self.required_checks_has_cla_required:
                return steps

            repo = self.api.repos.get(self.org_name, self.repo_name)
            default_branch = repo.default_branch

            # While the API docs claim that "contexts" is a required part
            # of the put body, it is only required if "checks" is not supplied.
            required_status_checks = {
                "strict": False,
                "checks": [
                    self.cla_check,
                ],
            }

            if not self.has_a_branch_protection_rule:
                # The easy case where we don't already have branch protection setup.
                # Might not work actually because of the bug we found below.  We'll need
                # to test against github to verify.
                params = {
                    "owner": self.org_name,
                    "repo": self.repo_name,
                    "branch": default_branch,
                    "required_status_checks": required_status_checks,
                    "enforce_admins": None,
                    "required_pull_request_reviews": None,
                    "restrictions": None,
                }

                if is_empty(self.api, self.org_name, self.repo_name):
                    steps.append(
                        "Repo has no branches, can't add branch protection rule yet."
                    )
                else:
                    if not dry_run:
                        self._update_branch_protection(params)

                    steps.append(
                        f"Added new branch protection with `openedx/cla` as a required check."
                    )

                return steps

            # There's already a branch protection rule, so we need to make sure
            # not to clobber the existing checks or settings.
            params = self._get_update_params_from_get_branch_protection()
            steps.append(f"State Before Update: {pformat(dict(params))}")

            if not self.branch_protection_has_required_checks:
                # We need to add a check object to the params we get
                # since this branch protection rule has no required checks.
                steps.append(f"Adding a new required check.\n{required_status_checks}")
                params["required_status_checks"] = required_status_checks
            else:
                # There is already a set of required checks, we just need to
                # add our new check to the existing list.
                steps.append(
                    f"Adding `openedx/cla` as a new required check to existing branch protection."
                )
                params["required_status_checks"]["checks"].append(self.cla_check)

            if not self.required_checks_has_cla_required:
                # Have to do this because of a bug in GhAPI see
                # _update_branch_protection docstring for more details.
                steps.append(f"Update we're requesting: {pformat(dict(params))}")
                if not dry_run:
                    self._update_branch_protection(params)
                # self.api.repos.update_branch_protection(**params)
        except HTTP4xxClientError as err:
            # Print the steps before raising the existing exception so we have
            # some more context on what might have happened.
            click.echo("\n".join(steps))
            click.echo(err.fp.read().decode("utf-8"))
            raise
        except requests.HTTPError as err:
            # Print the steps before raising the existing exception so we have
            # some more context on what might have happened.
            click.echo("\n".join(steps))
            click.echo(pformat(err.response.json()))
            raise

        return steps

    def _update_branch_protection(self, params):
        """
        Need to do this ourselves because of a bug in GhAPI that ignores
        `None` parameters and doesn't pass them through to the API.

        - https://github.com/fastai/ghapi/issues/81
        - https://github.com/fastai/ghapi/pull/91
        """
        params = dict(params)
        headers = self.api.headers
        url = (
            "https://api.github.com"
            + self.api.repos.update_branch_protection.path.format(**params)
        )
        resp = requests.put(  # pylint: disable=missing-timeout
            url, headers=headers, json=params
        )

        resp.raise_for_status()

    def _get_update_params_from_get_branch_protection(self):
        """
        Get the params needed to do an update operation that would produce
        the same branch protection as doing a get on this repo.

        We'll need this in cases where there are already some branch protection
        rules on the default branch and we want to update only some it without
        resetting the rest of it.
        """

        # TODO: Could use Glom here in the future, but didn't need it.
        repo = self.api.repos.get(self.org_name, self.repo_name)
        default_branch = repo.default_branch
        protection = self.api.repos.get_branch_protection(
            self.org_name, self.repo_name, default_branch
        )

        required_checks = None
        if "required_status_checks" in protection:
            # While the API docs claim that "contexts" is a required part
            # of the put body, it is only required if "checks" is not supplied.
            # The GET endpoint provides the curent set of required checks in both
            # format. So we only use the new "checks" format in our PUT params.
            required_checks = {
                "strict": protection.required_status_checks.strict,
                "checks": list(protection.required_status_checks.checks),
            }

        required_pr_reviews = None
        if "required_pull_request_reviews" in protection:
            required_pr_reviews = {
                "dismiss_stale_reviews": protection.required_pull_request_reviews.dismiss_stale_reviews,
                "require_code_owner_reviews": protection.required_pull_request_reviews.require_code_owner_reviews,
                "required_approving_review_count": protection.required_pull_request_reviews.required_approving_review_count,
            }

        restrictions = None
        if "restrictions" in protection:
            restrictions = {
                "users": [user.login for user in protection.restrictions.users],
                "teams": [team.slug for team in protection.restrictions.teams],
                "apps": [app.slug for app in protection.restrictions.apps],
            }

        params = {
            "owner": self.org_name,
            "repo": self.repo_name,
            "branch": default_branch,
            "required_status_checks": required_checks,
            "enforce_admins": True if protection.enforce_admins.enabled else None,
            "required_pull_request_reviews": required_pr_reviews,
            "restrictions": restrictions,
        }

        return params


@Check.register
class NoDirectUsers(Check):
    """
    Users should not have direct repo access
    """

    def __init__(self, api: GhApi, org: str, repo: str):
        super().__init__(api, org, repo)
        self.users_list = []

    def is_relevant(self) -> bool:
        """
        All non security fork repos, public or private.
        """
        return not is_security_private_fork(self.api, self.org_name, self.repo_name)

    def check(self) -> tuple[bool, str]:
        """
        Verify whether or not the check is failing.

        This should not change anything and should not have a side-effect
        other than populating `self` with any data that is needed later for
        `fix` or `dry_run`.

        The string in the return tuple should be a human readable reason
        that the check failed.
        """
        self.users_list = list(all_paged_items(
            self.api.repos.list_collaborators, owner=self.org_name, repo=self.repo_name, affiliation='direct'
        ))
        users = [f"{user.login}: {user.role_name}" for user in self.users_list]
        if users:
            return (
                False,
                f"Some users have direct repo access:\n\t\t"
                + "\n\t\t".join(users),
            )
        return (True, "No user has direct repo access.")

    def dry_run(self):
        return self.fix(dry_run=True)

    def fix(self, dry_run=False):
        steps = []
        for user in self.users_list:
            if not dry_run:
                self.api.repos.remove_collaborator(
                    owner=self.org_name,
                    repo=self.repo_name,
                    username=user.login,
                )
            steps.append(
                f"Removed direct access to the repository for user {user.login}"
            )

        return steps


@Check.register
class EnsureNoOutsideCollaborators(Check):
    """
    Repository shouldn't have outside collaborators
    """

    def __init__(self, api: GhApi, org: str, repo: str):
        super().__init__(api, org, repo)
        self.users_list = []

    def is_relevant(self) -> bool:
        """
        All non security fork repos, public or private.
        """
        return not is_security_private_fork(self.api, self.org_name, self.repo_name)

    def check(self) -> tuple[bool, str]:
        """
        Verify whether or not the check is failing.

        This should not change anything and should not have a side-effect
        other than populating `self` with any data that is needed later for
        `fix` or `dry_run`.

        The string in the return tuple should be a human readable reason
        that the check failed.
        """
        self.users_list = list(all_paged_items(
            self.api.repos.list_collaborators, owner=self.org_name, repo=self.repo_name, affiliation='outside'
        ))
        users = [f"{user.login}: {user.role_name}" for user in self.users_list]
        if users:
            return (
                False,
                f"The repo has some outside collaborators:\n\t\t"
                + "\n\t\t".join(users),
            )
        return (True, "The repo doesn't have any outside collaborators.")

    def dry_run(self):
        return self.fix(dry_run=True)

    def fix(self, dry_run=False):
        steps = []
        for user in self.users_list:
            if not dry_run:
                self.api.repos.remove_collaborator(
                    owner=self.org_name,
                    repo=self.repo_name,
                    username=user.login,
                )
            steps.append(
                f"Removed outside collaborator {user.login}"
            )

        return steps


@click.command()
@click.option(
    "--github-token",
    "_github_token",
    envvar="GITHUB_TOKEN",
    required=True,
    help="A github personal access token.",
)
@click.option(
    "--org",
    "org",
    default="openedx",
    help="The github org that you wish check.",
)
@click.option(
    "--dry-run/--no-dry-run",
    "-n",
    default=True,
    is_flag=True,
    help="Show what changes would be made without making them.",
)
@click.option(
    "--check",
    "-c",
    "check_names",
    default=None,
    multiple=True,
    type=click.Choice(Check.get_registered_checks().keys(), case_sensitive=False),
    help=f"Limit to specific check(s), case-insensitive.",
)
@click.option(
    "--repo",
    "-r",
    "repos",
    default=None,
    multiple=True,
    help="Limit to specific repo(s).",
)
@click.option(
    "--start-at",
    "-s",
    default=None,
    help="Which repo in the list to start running checks at.",
)
def main(org, dry_run, _github_token, check_names, repos, start_at):
    """
    Entry point for command-line invocation.
    """
    # pylint: disable=too-many-locals,too-many-branches
    api = GhApi()
    if not repos:
        repos = [
            repo.name
            for repo in all_paged_items(
                api.repos.list_for_org,
                org,
                sort="created",
                direction="desc",
            )
        ]

    if dry_run:
        click.secho("DRY RUN MODE: ", fg="yellow", bold=True, nl=False)
        click.secho("No Actual Changes Being Made", fg="yellow")

    if check_names:
        active_checks = [Check.get_registered_checks()[check_name] for check_name in check_names]
    else:
        active_checks = list(Check.get_registered_checks().values())
    click.secho(f"The following checks will be run:", fg="magenta", bold=True)
    active_checks_string = "\n".join(
        "\t" + check_cls.__name__ for check_cls in active_checks
    )
    click.secho(active_checks_string, fg="magenta")

    before_start_at = bool(start_at)
    for repo in repos:
        if repo == start_at:
            before_start_at = False

        if before_start_at:
            continue

        click.secho(f"{repo}: ", bold=True)
        for CheckType in active_checks:
            check = CheckType(api, org, repo)

            if check.is_relevant():
                result = check.check()
                if result[0]:
                    color = "green"
                else:
                    color = "red"

                click.secho(f"\t{result[1]}", fg=color)

                if dry_run:
                    try:
                        steps = check.dry_run()
                        steps_color = "yellow"
                    except HTTP4xxClientError as err:
                        click.echo(err.fp.read().decode("utf-8"))
                        raise
                else:
                    try:
                        steps = check.fix()
                        steps_color = "green"
                    except HTTP4xxClientError as err:
                        click.echo(err.fp.read().decode("utf-8"))
                        raise

                if steps:
                    click.secho("\tSteps:\n\t\t", fg=steps_color, nl=False)
                    click.secho(
                        "\n\t\t".join([step.replace("\n", "\n\t\t") for step in steps])
                    )
            else:
                click.secho(
                    f"\tSkipping {CheckType.__name__} as it is not relevant on this repo.",
                    fg="cyan",
                )


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
