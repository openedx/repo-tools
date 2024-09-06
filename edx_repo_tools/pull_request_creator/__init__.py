"""
Class helps create GitHub Pull requests
"""
# pylint: disable=missing-class-docstring,missing-function-docstring,attribute-defined-outside-init
import logging
import re
import os
import time
from ast import literal_eval

import click
import requests
from git import Git, Repo
from github import Github, GithubObject, InputGitAuthor, InputGitTreeElement
from packaging.version import Version


logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.INFO)


@click.command()
@click.option(
    '--repo-root',
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
    required=True,
    help="Directory containing local copy of repository"
)
@click.option(
    '--base-branch-name',
    required=True,
    help="Base name for branch to create. Full branch name will be like repo-tools/BASENAME-1234567."
)
@click.option(
    '--target-branch',
    required=False,
    default="master",
    help="Target branch against which we have to open a PR",
)
@click.option('--commit-message', required=True)
@click.option('--pr-title', required=True)
@click.option('--pr-body', required=True)
@click.option(
    '--user-reviewers',
    default='',
    help="Comma separated list of Github users to be tagged on pull requests"
)
@click.option(
    '--team-reviewers',
    default='',
    help=("Comma separated list of Github teams to be tagged on pull requests. "
          "NOTE: Teams must have explicit write access to the repo, or "
          "Github will refuse to tag them.")
)
@click.option(
    '--delete-old-pull-requests/--no-delete-old-pull-requests',
    default=True,
    help="If set, delete old branches with the same base branch name and close their PRs"
)
@click.option(
    '--force-delete-old-prs/--no-force-delete-old-prs',
    default=False,
    help="If set, force delete old branches with the same base branch name and close their PRs"
)
@click.option(
    '--draft', is_flag=True
)
@click.option(
    '--output-pr-url-for-github-action/--no-output-pr-url-for-github-action',
    default=False,
    help="If set, print resultant PR in github action set output sytax"
)
@click.option(
    '--untracked-files-required',
    required=False,
    help='If set, add Untracked files to the PR as well'
)
def main(
    repo_root, base_branch_name, target_branch,
    commit_message, pr_title, pr_body,
    user_reviewers, team_reviewers,
    delete_old_pull_requests, draft, output_pr_url_for_github_action,
    untracked_files_required, force_delete_old_prs
):
    """
    Create a pull request with these changes in the repo.

    Required environment variables:

    - GITHUB_TOKEN
    - GITHUB_USER_EMAIL
    """
    creator = PullRequestCreator(
        repo_root=repo_root,
        branch_name=base_branch_name,
        target_branch=target_branch,
        commit_message=commit_message,
        pr_title=pr_title, pr_body=pr_body,
        user_reviewers=user_reviewers,
        team_reviewers=team_reviewers,
        draft=draft,
        output_pr_url_for_github_action=output_pr_url_for_github_action,
        force_delete_old_prs=force_delete_old_prs
    )
    creator.create(delete_old_pull_requests, untracked_files_required)


class GitHubHelper:  # pylint: disable=missing-class-docstring

    def __init__(self):
        self._set_github_token()
        self._set_user_email()
        self._set_github_instance()
        self.AUTOMERGE_ACTION_VAR = 'AUTOMERGE_PYTHON_DEPENDENCIES_UPGRADES_PR'

    # FIXME: Does nothing, sets variable to None if env var missing
    def _set_github_token(self):
        try:
            self.github_token = os.environ.get('GITHUB_TOKEN')
        except Exception as error:
            raise Exception(
                "Could not find env variable GITHUB_TOKEN. "
                "Please make sure the variable is set and try again."
            ) from error

    # FIXME: Does nothing, sets variable to None if env var missing
    def _set_user_email(self):
        try:
            self.github_user_email = os.environ.get('GITHUB_USER_EMAIL')
        except Exception as error:
            raise Exception(
                "Could not find env variable GITHUB_USER_EMAIL. "
                "Please make sure the variable is set and try again."
            ) from error

    def _set_github_instance(self):
        try:
            self.github_instance = Github(self.github_token)
        except Exception as error:
            raise Exception(
                "Failed connecting to Github. " +
                "Please make sure the github token is accurate and try again."
            ) from error

    def _add_reason(self, req, reason):
        req['reason'] = reason
        return req

    def _add_comment_about_reqs(self, pr, summary, reqs):
        separator = "\n"
        pr.create_issue_comment(
            f"{summary}.</br> \n {separator.join(self.make_readable_string(req) for req in reqs)}"
        )

    def get_github_instance(self):
        return self.github_instance

    def get_github_token(self):
        return self.github_token

    # FIXME: Probably can end up picking repo from wrong org if two
    # repos have the same name in different orgs.
    #
    # Use repo_from_remote instead, and delete this when no longer in use.
    def connect_to_repo(self, github_instance, repo_name):
        """
        Get the repository object of the desired repo.
        """
        repos_list = github_instance.get_user().get_repos()
        for repo in repos_list:
            if repo.name == repo_name:
                return repo

        raise Exception(
            "Could not connect to the repository: {}. "
            "Please make sure you are using the correct "
            "credentials and try again.".format(repo_name)
        )

    def repo_from_remote(self, repo_root, remote_name_allow_list=None):
        """
        Get the repository object for a repository with a Github remote.

        Optionally restrict the remotes under consideration by passing a list
        of names as``remote_name_allow_list``, e.g. ``['origin']``.
        """
        patterns = [
            r"git@github\.com:(?P<name>[^/?#]+/[^/?#]+?).git",
            # Non-greedy match for repo name so that optional .git on
            # end is not included in repo name match.
            r"https?://(www\.)?github\.com/(?P<name>[^/?#]+/[^/?#]+?)(/|\.git)?"
        ]
        for remote in Repo(repo_root).remotes:
            if remote_name_allow_list and remote.name not in remote_name_allow_list:
                continue
            for url in remote.urls:
                for pattern in patterns:
                    m = re.fullmatch(pattern, url)
                    if m:
                        fullname = m.group('name')
                        logger.info("Discovered repo %s in remotes", fullname)
                        return self.github_instance.get_repo(fullname)
        raise Exception("Could not find a Github URL among repo's remotes")

    def branch_exists(self, repository, branch_name):
        """
        Checks to see if this branch name already exists
        """
        try:
            repository.get_branch(branch_name)
        except:  # pylint: disable=bare-except
            return False
        return True

    def get_current_commit(self, repo_root):
        """
        Get current commit ID of repo at repo_root.
        """
        return Git(repo_root).rev_parse('HEAD')

    def get_updated_files_list(self, repo_root, untracked_files_required=False):
        """
        Use the Git library to run the ls-files command to find
        the list of files updated.
        """
        git_instance = Git(repo_root)
        git_instance.init()

        if untracked_files_required:
            modified_files = git_instance.ls_files("--modified")
            untracked_files = git_instance.ls_files("--others", "--exclude-standard")
            updated_files = modified_files + '\n' + untracked_files \
                if (len(modified_files) > 0 and len(untracked_files) > 0) \
                else modified_files + untracked_files

        else:
            updated_files = git_instance.ls_files("--modified")

        if len(updated_files) > 0:
            return updated_files.split("\n")
        else:
            return []

    def create_branch(self, repository, branch_name, sha):
        """
        Create a new branch with the given sha as its head.
        """
        try:
            branch_object = repository.create_git_ref(branch_name, sha)
        except Exception as error:
            raise Exception(
                "Unable to create git branch: {}. "
                "Check to make sure this branch doesn't already exist.".format(branch_name)
            ) from error
        return branch_object

    def close_existing_pull_requests(self, repository, user_login, user_name, target_branch='master',
                                     branch_name_filter=None):
        """
        Close any existing PR's by the bot user in this PR. This will help
        reduce clutter, since any old PR's will be obsolete.
        If function branch_name_filter is specified, it will be called with
        branch names of PRs. The PR will only be closed when the function
        returns true.
        """
        pulls = repository.get_pulls(state="open")
        deleted_pull_numbers = []
        for pr in pulls:
            user = pr.user
            if user.login == user_login and user.name == user_name and pr.base.ref == target_branch:
                branch_name = pr.head.ref
                if branch_name_filter and not branch_name_filter(branch_name):
                    continue
                logger.info("Deleting PR: #%s", pr.number)
                pr.create_issue_comment("Closing obsolete PR.")
                pr.edit(state="closed")
                deleted_pull_numbers.append(pr.number)

                self.delete_branch(repository, branch_name)
        return deleted_pull_numbers

    def create_pull_request(self, repository, title, body, base, head, user_reviewers=GithubObject.NotSet,
                            team_reviewers=GithubObject.NotSet, verify_reviewers=True, draft=False):
        """
        Create a new pull request with the changes in head. And tag a list of teams
        for a review.
        """
        try:
            pull_request = repository.create_pull(
                title=title,
                body=body,
                base=base,
                head=head,
                draft=draft
            )
        except Exception as e:
            raise e

        try:
            any_reviewers = (user_reviewers is not GithubObject.NotSet or team_reviewers is not GithubObject.NotSet)
            if any_reviewers:
                logger.info("Tagging reviewers: users=%s and teams=%s", user_reviewers, team_reviewers)
                pull_request.create_review_request(
                    reviewers=user_reviewers,
                    team_reviewers=team_reviewers,
                )
                if verify_reviewers:
                    # Sometimes GitHub can't find the pull request we just made.
                    # Try waiting a moment before asking about it.
                    time.sleep(5)
                    self.verify_reviewers_tagged(pull_request, user_reviewers, team_reviewers)

        except Exception as e:
            raise Exception(
                "Some reviewers could not be tagged on new PR "
                "https://github.com/{}/pull/{}".format(repository.full_name, pull_request.number)
            ) from e

        # Do this in upgrade PRs only
        if pull_request.title == 'chore: Upgrade Python requirements':
            self.verify_upgrade_packages(pull_request)

        return pull_request

    def verify_reviewers_tagged(self, pull_request, requested_users, requested_teams):
        """
        Assert if the reviewers we requested were tagged on the PR for review.

        Considerations:

        - Teams cannot be tagged on a PR unless that team has explicit write
          access to the repo.
        - Github may have independently tagged additional users or teams
          based on a CODEOWNERS file.
        """
        tagged_for_review = pull_request.get_review_requests()

        tagged_users = [user.login for user in tagged_for_review[0]]
        if not (requested_users is GithubObject.NotSet or set(requested_users) <= set(tagged_users)):
            logger.info("User taggging failure: Requested %s, actually tagged %s", requested_users, tagged_users)
            raise Exception('Some of the requested reviewers were not tagged on PR for review')

        tagged_teams = [team.name for team in tagged_for_review[1]]
        if not (requested_teams is GithubObject.NotSet or set(requested_teams) <= set(tagged_teams)):
            logger.info("Team taggging failure: Requested %s, actually tagged %s", requested_teams, tagged_teams)
            raise Exception('Some of the requested teams were not tagged on PR for review')

    def verify_upgrade_packages(self, pull_request):
        """
        Iterate on pull request diff and parse the packages and check the versions.
        If all versions are upgrading then add a label ready for auto merge. In case of any downgrade package
        add a comment on PR.
        """
        location = None
        location = pull_request._headers['location']    # pylint: disable=protected-access
        logger.info(location)

        if not location:
            return

        logger.info('Hitting pull request for difference')
        headers = {"Accept": "application/vnd.github.v3.diff", "Authorization": f'Bearer {self.github_token}'}

        load_content = requests.get(location, headers=headers, timeout=5)
        txt = ''
        time.sleep(3)
        logger.info(load_content.status_code)

        if load_content.status_code == 200:
            txt = load_content.content.decode('utf-8')
            valid_reqs, suspicious_reqs = self.compare_pr_differnce(txt)

            self._add_comment_about_reqs(pull_request, "List of packages in the PR without any issue", valid_reqs)

            if not suspicious_reqs and valid_reqs:
                if self.check_automerge_variable_value(location):
                    pull_request.set_labels('Ready to Merge')
                    logger.info("Total valid upgrades are %s", valid_reqs)
            else:
                self._add_comment_about_reqs(pull_request, "These Packages need manual review.", suspicious_reqs)

        else:
            logger.info("No package available for comparison.")

    def check_automerge_variable_value(self, location):
        """
        Check whether repository has the `AUTOMERGE_PYTHON_DEPENDENCIES_UPGRADES_PR` variable
        with `True` value exists.
        """
        link = location.split('pulls')
        get_repo_variable = link[0] + 'actions/variables/' + self.AUTOMERGE_ACTION_VAR
        logger.info('Hitting repository to check AUTOMERGE_ACTION_VAR settings.')

        headers = {"Accept": "application/vnd.github+json", "Authorization": f'Bearer {self.github_token}'}
        load_content = requests.get(get_repo_variable, headers=headers, timeout=5)
        time.sleep(1)

        if load_content.status_code == 200:
            val = literal_eval(load_content.json()['value'])
            logger.info(f"AUTOMERGE_ACTION_VAR value is {val}")
            return val

        return False

    def compare_pr_differnce(self, txt):
        """ Parse the content and extract packages for comparison. """
        regex = re.compile(r"(?P<change>[\-\+])(?P<name>[\w][\w\-\[\]]+)==(?P<version>\d+\.\d+(\.\d+)?(\.[\w]+)?)")
        reqs = {}
        if not txt:
            return [], []

        # skipping zeroth index  as it will be empty
        files = txt.split("diff --git")[1:]
        for file in files:
            lines = file.split("\n")
            filename_match = re.search(r"[\w\-\_]*.txt", lines[0])
            if not filename_match:
                continue
            filename = filename_match[0]
            reqs[filename] = {}
            for line in lines:
                match = re.match(regex, line)
                if match:
                    groups = match.groupdict()
                    keys = ('new_version', 'old_version') if groups['change'] == '+' \
                        else ('old_version', 'new_version')
                    if groups['name'] in reqs[filename]:
                        reqs[filename][groups['name']][keys[0]] = groups['version']
                    else:
                        reqs[filename][groups['name']] = {keys[0]: groups['version'], keys[1]: None}
        combined_reqs = []
        for file, lst in reqs.items():
            for name, versions in lst.items():
                combined_reqs.append(
                    {"name": name, 'old_version': versions['old_version'], 'new_version': versions['new_version']}
                )

        unique_reqs = [dict(s) for s in set(frozenset(d.items()) for d in combined_reqs)]
        valid_reqs = []
        suspicious_reqs = []
        for req in unique_reqs:
            if req['new_version'] and req['old_version']:  # if both values exits then do version comparison
                old_version = Version(req['old_version'])
                new_version = Version(req['new_version'])

                # skip, if the package location is changed in txt file only and both versions are same
                if old_version == new_version:
                    continue
                if new_version > old_version:
                    if new_version.major == old_version.major:
                        valid_reqs.append(req)
                    else:
                        suspicious_reqs.append(self._add_reason(req, "MAJOR"))
                else:
                    suspicious_reqs.append(self._add_reason(req, "DOWNGRADE"))
            else:
                if req['new_version']:
                    suspicious_reqs.append(self._add_reason(req, "NEW"))
                else:
                    suspicious_reqs.append(self._add_reason(req, "REMOVED"))

        return sorted(valid_reqs, key=lambda d: d['name']), sorted(suspicious_reqs, key=lambda d: d['name'])

    def make_readable_string(self, req):
        """making string for readability"""
        if 'reason' in req:
            if req['reason'] == 'NEW':
                return f"- **[{req['reason']}]**  `{req['name']}`" \
                       f" (`{req['new_version']}`) added to the requirements"
            if req['reason'] == 'REMOVED':
                return f"- **[{req['reason']}]**  `{req['name']}`" \
                       f" (`{req['old_version']}`) removed from the requirements"
            # either major version bump or downgraded
            return f"- **[{req['reason']}]** `{req['name']}` " \
                   f"changes from `{req['old_version']}` to `{req['new_version']}`"
        # valid requirement
        return f"- `{req['name']}` changes from `{req['old_version']}` to `{req['new_version']}`"

    def delete_branch(self, repository, branch_name):
        """
        Delete a branch from a repository.
        """
        logger.info("Deleting Branch: %s", branch_name)
        try:
            ref = "heads/{}".format(branch_name)
            branch_object = repository.get_git_ref(ref)
            branch_object.delete()
        except Exception as error:
            raise Exception(
                "Failed to delete branch"
            ) from error

    def get_file_contents(self, repo_root, file_path):
        """
        Return contents of local file
        """
        try:
            full_file_path = os.path.join(repo_root, file_path)
            with open(full_file_path, 'r', encoding='utf-8') as opened_file:
                data = opened_file.read()
        except Exception as error:
            raise Exception(
                "Unable to read file: {}".format(file_path)
            ) from error

        return data

    # pylint: disable=missing-function-docstring
    def update_list_of_files(self, repository, repo_root, file_path_list, commit_message, sha, username):
        input_trees_list = []
        base_git_tree = repository.get_git_tree(sha)
        for file_path in file_path_list:
            content = self.get_file_contents(repo_root, file_path)
            input_tree = InputGitTreeElement(file_path, "100644", "blob", content=content)
            input_trees_list.append(input_tree)
        if len(input_trees_list) > 0:
            new_git_tree = repository.create_git_tree(input_trees_list, base_tree=base_git_tree)
            parents = [repository.get_git_commit(sha)]
            author = InputGitAuthor(username, self.github_user_email)
            commit_sha = repository.create_git_commit(
                commit_message, new_git_tree, parents, author=author, committer=author
            ).sha
            return commit_sha

        return None


class PullRequestCreator:

    def __init__(self, repo_root, branch_name, user_reviewers, team_reviewers, commit_message, pr_title,
                 pr_body, target_branch='master', draft=False, output_pr_url_for_github_action=False,
                 force_delete_old_prs=False):
        self.branch_name = branch_name
        self.pr_body = pr_body
        self.pr_title = pr_title
        self.commit_message = commit_message
        self.team_reviewers = team_reviewers
        self.user_reviewers = user_reviewers
        self.repo_root = repo_root
        self.target_branch = target_branch
        self.draft = draft
        self.output_pr_url_for_github_action = output_pr_url_for_github_action
        self.force_delete_old_prs = force_delete_old_prs

    github_helper = GitHubHelper()

    def _get_github_instance(self):
        return self.github_helper.get_github_instance()

    def _get_user(self):
        return self.github_instance.get_user()

    def _set_repository(self):
        self.repository = self.github_helper.repo_from_remote(self.repo_root, ['origin'])

    def _set_updated_files_list(self, untracked_files_required=False):
        self.updated_files_list = self.github_helper.get_updated_files_list(self.repo_root, untracked_files_required)

    def _create_branch(self, commit_sha):
        self.github_helper.create_branch(self.repository, self.branch, commit_sha)

    def _set_github_data(self, untracked_files_required=False):
        logger.info("Authenticating with Github")
        self.github_instance = self._get_github_instance()
        self.user = self._get_user()

        logger.info("Trying to connect to repo")
        self._set_repository()
        logger.info("Connected to %s", self.repository)
        self._set_updated_files_list(untracked_files_required)
        self.base_sha = self.github_helper.get_current_commit(self.repo_root)
        self.branch = "refs/heads/repo-tools/{}-{}".format(self.branch_name, self.base_sha[:7])

    def _branch_exists(self):
        return self.github_helper.branch_exists(self.repository, self.branch)

    def _create_new_branch(self):
        logger.info("updated files: %s", self.updated_files_list)
        commit_sha = self.github_helper.update_list_of_files(
            self.repository,
            self.repo_root,
            self.updated_files_list,
            self.commit_message,
            self.base_sha,
            self.user.name
        )
        self._create_branch(commit_sha)

    def _create_new_pull_request(self):
        # If there are reviewers to be added, split them into python lists
        if isinstance(self.user_reviewers, str) and self.user_reviewers:
            user_reviewers = self.user_reviewers.split(',')
        else:
            user_reviewers = GithubObject.NotSet

        if isinstance(self.team_reviewers, str) and self.team_reviewers:
            team_reviewers = self.team_reviewers.split(',')
        else:
            team_reviewers = GithubObject.NotSet

        pr = self.github_helper.create_pull_request(
            self.repository,
            self.pr_title,
            self.pr_body,
            self.target_branch,
            self.branch,
            user_reviewers=user_reviewers,
            team_reviewers=team_reviewers,
            # TODO: Remove hardcoded check in favor of a new --verify-reviewers CLI option
            verify_reviewers=self.branch_name != 'cleanup-python-code',
            draft=self.draft
        )
        logger.info(
            "Created PR: https://github.com/%s/pull/%s",
            self.repository.full_name,
            pr.number,
        )
        if self.output_pr_url_for_github_action:
            # using print rather than logger to avoid the logger
            # prepending anything past which github actions wouldn't parse
            print(f'generated_pr=https://github.com/{self.repository.full_name}/pull/{pr.number} >> $GITHUB_OUTPUT')

    def delete_old_pull_requests(self):
        logger.info("Checking if there's any old pull requests to delete")
        # Only delete old PRs with the same base name
        # The prefix used to be 'jenkins' before we changed it to 'repo-tools'
        filter_pattern = "(jenkins|repo-tools)/{}-[a-zA-Z0-9]*".format(re.escape(self.branch_name))
        deleted_pulls = self.github_helper.close_existing_pull_requests(
            self.repository, self.user.login,
            self.user.name, self.target_branch,
            branch_name_filter=lambda name: re.fullmatch(filter_pattern, name)
        )

        for num, deleted_pull_number in enumerate(deleted_pulls):
            if num == 0:
                self.pr_body += "\n\nDeleted obsolete pull_requests:"
            self.pr_body += "\nhttps://github.com/{}/pull/{}".format(self.repository.full_name,
                                                                     deleted_pull_number)

    def _delete_old_branch(self):
        logger.info("Deleting existing old branch with same name")
        branch_name = self.branch.split('/', 2)[2]
        self.github_helper.delete_branch(self.repository, branch_name)

    def create(self, delete_old_pull_requests, untracked_files_required=False):
        self._set_github_data(untracked_files_required)

        if not self.updated_files_list:
            logger.info("No changes needed")
            return

        if self.force_delete_old_prs or delete_old_pull_requests:
            self.delete_old_pull_requests()
            if self._branch_exists():
                self._delete_old_branch()

        elif self._branch_exists():
            logger.info("Branch for this sha already exists")
            return

        self._create_new_branch()

        self._create_new_pull_request()


if __name__ == '__main__':
    main(auto_envvar_prefix="PR_CREATOR")  # pylint: disable=no-value-for-parameter
