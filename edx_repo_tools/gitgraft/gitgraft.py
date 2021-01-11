"""
Pretty simple module to help move commits between git repos with broken common history, such as ones created through
a git filter subdirectory. Has some tools for speeding up activities on large repos such as limiting history search
by include / ignore directives and by date.
"""
import io
import os
import re
import hashlib
import configparser
import datetime
import pprint
from collections import OrderedDict

import click
import git
from git.util import join_path as join

# Regex to find commit shas in previously grafted commit messages
SHA_MESSAGE_TOKEN = re.compile(r'(>>)([0-9a-fA-F]{40})(<<)')


class InputException(Exception):
    """
    Generic exception for broken inputs
    """
    pass


class Grafter:
    """
    Does all of the work of grafting including:
    - Compiling a list of commits across both repos for the given time period
    - Mapping paths from the old repo to the new based on given tracking information
    - Creating a new branch for the graft
    - Creating commits to the new branch that mirror relevant parts of commits made on the old repo
    - Marking commits as grafted in commit messages
    """
    # When we clone_commits the newly created branch will be stored here, unless it's a dry run
    output_branch = None

    # Dict of potentially relevant commits (contain changes to files in the tracked paths) that exist in both repos for
    # the given time period. Needs to be ordered so we can iterate over them in the order the commits were made.
    candidate_commits = OrderedDict()

    # For reporting purposes we store off files changed in candidate_commits to the original repo that *may* have
    # impacted the new repo but don't exist there. Helps in debugging issues with tracked paths.
    unmatched_original_files = set()

    def __init__(self, original_repo_name, original_repo_path, branched_repo_path, max_lookback_days=180,
                 original_repo_head="master", branched_repo_head="master", tracked=None, original_ignore=None,
                 branched_ignore=None, verbose=False, dry_run=False):
        """
        :param original_repo_path: Relative or absolute path to the original repo's location on this machine
        :param branched_repo_path: Relative or absolute path to the branched repo's location on this machine
        :param max_lookback_days: How many days back to look for changes to carry over, fewer is faster
        :param original_repo_head: Branch to use in the original repo
        :param branched_repo_head: Branch to use in the branched repo
        :param tracked: Dict mapping original repo relative paths to branched repo relative paths ex:
                        {
                            'old/path/code': 'new/path/stored/elsewhere/code',
                            'old/path/file.py': 'new/path/libraries/file.py'
                        }
        :param original_ignore: List of paths inside the tracked paths to ignore commits from in the original repo
        :param branched_ignore: List of paths inside the tracked paths to ignore commits from in the branched repo
        :param verbose: Turn on / off verbose output
        :param dry_run: When True, does not create a new branch or perform commits
        """
        self.pprint = pprint.PrettyPrinter(indent=3)

        self.dry_run = dry_run
        self.verbose = verbose

        # Get the epoch time of our max lookback
        epoch = datetime.datetime.utcfromtimestamp(0)
        self.oldest_lookback_datetime = datetime.datetime.utcnow() - datetime.timedelta(days=max_lookback_days)
        self.oldest_lookback_epoch = (self.oldest_lookback_datetime - epoch).total_seconds()

        self.original_repo_name = original_repo_name

        # Set up our repos
        self.original_repo_path = original_repo_path
        self.original_repo = git.Repo(original_repo_path)

        self.branched_repo_path = branched_repo_path
        self.branched_repo = git.Repo(branched_repo_path)

        self.sanity_check_repos()

        # Set up our branches
        self.original_repo_head = original_repo_head
        self.original_repo.git.checkout(original_repo_head)

        self.branched_repo_head = branched_repo_head
        self.branched_repo.git.checkout(branched_repo_head)

        self.sanity_check_branches()

        # Set up our tracked and ignored paths
        self.tracked = tracked

        self.original_ignore = original_ignore
        self.sanity_check_paths(self.original_repo_path, self.tracked.keys(), "Tracked")
        self.sanity_check_paths(self.original_repo_path, self.original_ignore, "Ignore")

        self.branched_ignore = branched_ignore
        self.sanity_check_paths(self.branched_repo_path, self.tracked.values(), "Tracked")
        self.sanity_check_paths(self.branched_repo_path, self.branched_ignore, "Ignore")

    def sanity_check_repos(self):
        """
        Make sure the repos exist, are not empty, and are not dirty.

        :raises InputException if conditions are not met
        """
        errors = []
        for repo in (self.original_repo, self.branched_repo):
            if repo.bare:
                errors.append(f"ERROR- repository {repo.working_tree_dir} is empty!")

            if repo.is_dirty():
                errors.append(
                    "ERROR- repository {} is dirty! Please commit any changes before running.".format(
                        repo.working_tree_dir
                    )
                )

        self.fail_on_errors(errors)

    def sanity_check_branches(self):
        """
        Make sure our branches are attached, local, and valid

        :raises InputException if conditions are not met
        """
        errors = []
        for repo in (self.original_repo, self.branched_repo):
            if repo.head.is_detached:
                errors.append(f"ERROR- branch head {repo.head.name} is detached!")

            if repo.head.is_remote():
                errors.append(f"ERROR- branch head {repo.head.name} is remote!")

            if not repo.head.is_valid():
                errors.append(f"ERROR- branch head {repo.head.name} is invalid!")

        self.fail_on_errors(errors)

    def sanity_check_paths(self, repo_path, paths, path_type):
        """
        Checks existence of a path in the given repo
        :param repo_path: Relative or absolute path to the top level of the repo
        :param paths: List of paths to test
        :param path_type: String to indicate what type of path was being tested in error messages
        :raises InputException if conditions are not met
        """
        errors = []
        for path in paths:
            full_path = join(repo_path, path)

            if not os.path.exists(full_path):
                errors.append(f"{path_type} path {full_path} does not exist!")
        self.fail_on_errors(errors)

    @staticmethod
    def fail_on_errors(errors):
        """
        Utility method to print and raise exceptions if any errors are passed in
        :param errors: List of error strings to output
        :raises InputException if errors is not empty
        """
        if len(errors):
            err_str = "\n".join(errors)
            print(err_str)
            raise InputException(err_str)

    @staticmethod
    def get_hexdigest_from_commit(commit):
        """
        Creates a reasonably unique sha1 hash for a given commit, based on that commit's metadata. Used to identify
        the same commit across repos since their git sha's will be different.
        :param commit: gitpython Commit object
        :return: sha1 hexdigest of some of the given commit's metadata
        """
        hsh = hashlib.sha1()
        hsh.update(b"%i" % commit.committed_date)
        hsh.update(b"%i" % commit.authored_date)
        hsh.update(commit.message.encode("utf-8"))
        hsh.update(commit.author.email.encode("utf-8"))
        hsh.update(commit.committer.email.encode("utf-8"))
        return hsh.hexdigest()

    def find_candidate_commits(self):
        """
        Walks backwards through time, populating self.candidate_commits with "commits of interest" from first the
        branched repo, then the original. Uses a combination of commit metadata and commit messages from previous grafts
        to match up commits that exist in both repos, leaving us with the ability to find commits that exist only in
        the original repo which we want to graft onto the new repo.
        """
        # If we've previously grafted a commit we'll pull the old sha out of the message and use it to prevent
        # duplicate graftings.
        found_grafted_commits = {}

        for repo, paths, repo_name in (
                (self.branched_repo, self.tracked.values(), "branched"),
                (self.original_repo, self.tracked.keys(), "original"),
        ):
            # Key into the self.candidate_commits[digest] dict so we can make this chunk of code reusable across
            # original and branched repos.
            commit_key = f"{repo_name}_commit"
            paths = list(paths)

            for commit in repo.commits(paths=paths):
                self.vprint(f"Processing commit: {commit.hexsha}")
                digest = self.get_hexdigest_from_commit(commit)

                if commit.committed_date < self.oldest_lookback_epoch:
                    break

                # Skip PR merges as they only yield empty commits for us.
                # TODO: Find a better way to check this. Diffs don't work.
                if commit.committer.name == "GitHub" or not len(commit.parents):
                    continue

                for i in commit.diff(commit.parents[0]):
                    # If any file in this commit is a valid candidate we keep the whole commit so we check them all
                    if not self.is_valid_candidate_path(i.a_path, repo_name):
                        continue

                    if digest not in self.candidate_commits:
                        self.candidate_commits[digest] = {
                            "branched_commit": None, "original_commit": None
                        }

                    self.candidate_commits[digest][commit_key] = commit

                    # This chunk is just to make sure we don't re-apply the same commits repeatedly. It looks for
                    # a token in the branched repo commits like this ">>3908512a0bd425de80222f3c4f64b65f7af4e7d7<<"
                    # which indicates a previous graft of that commit hash from the original repo.
                    #
                    # When we get to the original repo, if we run into those commits we can apply the actual commit
                    # hash in the branched repo to self.candidate_commits, which will exclude those commits from
                    # being cloned later.
                    if repo_name == "branched":
                        previous_graft_artifact = re.search(SHA_MESSAGE_TOKEN, commit.message)

                        if previous_graft_artifact:
                            found_grafted_commits[previous_graft_artifact.groups()[1]] = commit.hexsha
                    elif self.candidate_commits[digest]["branched_commit"] is None:
                        if commit.hexsha in found_grafted_commits:
                            self.candidate_commits[digest]["branched_commit"] = found_grafted_commits[commit.hexsha]

                    # Once we've stored off the commit, no need to check more files
                    break

    def try_map_path(self, source):
        """
        Find a path in the branched repo that best matches a given one in the original repo
        :param source: A path in the original repo
        :return: The best-matching path in the branched repo, or None if no mapping is found
        """
        match = None
        match_path = ""

        for tracked_src_path in self.tracked:
            if source.startswith(tracked_src_path):
                # Assumption here is that a longer path that matches is more specific, and so potentially better
                if not match or len(tracked_src_path) > len(match):
                    # Strip out the original base path and any lingering separators
                    extra = os.path.normpath(source.replace(tracked_src_path, "", 1).lstrip("/\\"))

                    # Make a new base path for the new repo, including any subdirs
                    check_path = os.path.join(self.branched_repo_path, self.tracked[tracked_src_path], extra)

                    if os.path.exists(check_path):
                        match = tracked_src_path
                        match_path = check_path
                    else:
                        self.vprint(f"{check_path} does not exist in branched repo, skipping.")
            else:
                self.vprint(f"{source} not in tracked path {tracked_src_path}")

        return match_path if match else None

    def clone_commits(self):
        """
        Copy the files of interest from a commit in the original repo to the branched repo and commit them there.
        """
        # Create a new branch in the branched repo
        if not self.dry_run:
            new_branch_name = "graft-%s" % datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            self.output_branch = self.branched_repo.create_head(new_branch_name)
            self.output_branch.checkout()

        # Move over every applicable commit from the old repo to the new branch, moving in chronological order
        # Extra list() call here is to work around reversed() not working with OrderedDicts in Python 3.4
        # https://bugs.python.org/issue19505
        for commit_dict in reversed(list(self.candidate_commits.values())):
            original_commit = commit_dict["original_commit"]

            # We only care about commits to the original branch that hadn't made it to the new branch
            if commit_dict["original_commit"] is None or commit_dict["branched_commit"] is not None:
                continue

            # Files to be included in this commit
            found_files = []

            # Loop through all of the files in the diff, see if any files are relevant and update them
            for i in original_commit.diff(original_commit.parents[0]):
                if not self.is_valid_candidate_path(i.a_path, "original"):
                    continue

                self.vprint("-----------------------------------------------")
                self.vprint(f"\nFiles in commit {original_commit.hexsha}")
                self.vprint(original_commit.stats.files, pretty=True)

                dest_path = self.try_map_path(i.a_path)

                if dest_path:
                    self.vprint(f"Copying {i.a_path} to {dest_path}")

                    if not self.dry_run:
                        with open(dest_path, 'wb') as f:
                            i.a_blob.stream_data(f)

                    found_files.append(dest_path)
                else:
                    self.unmatched_original_files.add(i.a_path)

            if len(found_files):
                fdate = datetime.datetime.fromtimestamp(original_commit.committed_date).isoformat()
                subject = original_commit.message.split("\n")[0].strip()
                msg = """{subject}

Grafting commit >>{sha}<< from {original_repo_name}
Original commit by {committer_name} on {date} with this message:
----------------------------------------------------------------
{message}""".format(sha=original_commit.hexsha, committer_name=original_commit.committer.name, date=fdate,
                    message=original_commit.message, subject=subject, original_repo_name=self.original_repo_name)

                print(msg)
                print("\n".join(found_files))
                print("\n\n")

                # if not self.dry_run:
                #    self.branched_repo.index.add(found_files)
                #    self.branched_repo.index.commit(msg)
            else:
                self.vprint(f"\n\nNothing to commit for original repo sha {original_commit.hexsha}")

        if not self.dry_run:
            print("--------------------------------------------------")
            print(f"Your branch has been changed to {self.output_branch}")
            print("--------------------------------------------------")

    def is_valid_candidate_path(self, path, repo_name):
        """
        When checking for candidate commits, see if a particular path is tracked and not ignored
        :param path: Relative path to check
        :param repo_name: "original" or "branched", used to locate tracked and ignored paths
        :return: True if the path is valid, otherwise False
        :raises AttributeError if an unknown repo name is passed in
        """
        if repo_name == "original":
            tracked = self.tracked.keys()
            ignore = self.original_ignore
        elif repo_name == "branched":
            tracked = self.tracked.values()
            ignore = self.branched_ignore
        else:
            raise AttributeError("Invalid repo name!")

        if any(path.startswith(i) for i in ignore):
            return False
        return any(path.startswith(i) for i in tracked)

    def vprint(self, string, pretty=False):
        """
        Prints a string only if it is verbose
        :param string: String to print
        :param pretty: Use prettyprint
        """
        if self.verbose:
            if pretty:
                self.pprint.pprint(string)
            else:
                print(string)

    def report(self):
        """
        Prints a short report with some information about the current state of the graft. Only really useful after
        find_candidate_commits and clone_commits have been called.
        """
        print("\nDebug Report:\n-----------------------------------------------")
        # TODO: Various other print statements should probably be moved in here and formatted correctly
        problematic_commits = set()

        for digest in self.candidate_commits:
            commit_dict = self.candidate_commits[digest]

            if commit_dict['original_commit'] is not None and commit_dict['branched_commit'] is not None:
                print(f"{digest} - exists in both repos!")
            elif commit_dict['branched_commit'] is not None:
                print("{} - commit {} only in branched repo".format(digest, commit_dict['branched_commit']))
            elif commit_dict['original_commit'] is not None:
                print("{} - commit {} only in original repo".format(digest, commit_dict['original_commit']))
                problematic_commits.add(commit_dict["original_commit"])

        print("\nCommits in original repo that were checked against:")
        self.pprint.pprint(problematic_commits)

        print("\n{} modified files in tracked paths that do not exist in branched".format(
            len(self.unmatched_original_files)))
        self.pprint.pprint(self.unmatched_original_files)


def process_config_str(config_str):
    """
    Takes potentially multi-line RawConfigParser-returned strings, strips them, and splits them by line.
    :param config_str: String parsed in by RawConfigParser
    :return: List of strings broken up and trimmed.
    """
    if config_str is not None:
        return [i.strip() for i in config_str.split("\n") if len(i.strip()) > 0]


def process_tracked_config_str(config_lst):
    """
    Takes a list generated by process_config_str and does transformations on it to make a dict of tracked paths
    :param config_lst: List of tracked path configuration lines such as "/foo/bar/baz > /bing/bang/bar/baz"
    :return: Dict of tracked paths in the form of {"/foo/bar/baz": "/bing/bang/bar/baz"}
    """
    tracked = {}
    for line in process_config_str(config_lst):
        try:
            source, dest = line.split(">")
            source = os.path.normpath(source.strip())
            dest = os.path.normpath(dest.strip())
            tracked[source] = dest
        except:
            raise InputException("Tracked paths configured incorrectly. Each line should look have a source path, "
                                 "relative to the original repo root, a right angle bracket (>), and a destination"
                                 "path relative to the branched repo root:"
                                 "source > dest")
    return tracked


@click.command()
@click.argument('conf', type=click.Path(exists=True))
@click.option('--dry_run', is_flag=True, help="Do a test run without creating a branch or commits")
@click.option('--verbose', is_flag=True, help="Verbose output")
def main(conf, dry_run, verbose):
    """
    Creates a "best-guess" copy of commits across two unrelated (no consistent history) github repositories
    """
    config = configparser.RawConfigParser()
    config.read(conf)

    orig_repo_name = config.get("repositories", "original_repository_name")
    orig = config.get("repositories", "original_repository")
    branched = config.get("repositories", "branched_repository")
    original_branch = process_config_str(config.get("repositories", "original_branch"))[0]
    branched_branch = process_config_str(config.get("repositories", "branched_branch"))[0]

    tracked = process_tracked_config_str(config.get("tracked_paths", "tracked"))
    original_ignored = process_config_str(config.get("tracked_paths", "original_ignored"))
    branched_ignored = process_config_str(config.get("tracked_paths", "branched_ignored"))

    grafter = Grafter(orig_repo_name,
                      orig,
                      branched,
                      tracked=tracked,
                      original_ignore=original_ignored,
                      branched_ignore=branched_ignored,
                      original_repo_head=original_branch,
                      branched_repo_head=branched_branch,
                      dry_run=dry_run,
                      verbose=verbose)
    grafter.find_candidate_commits()
    grafter.clone_commits()

    if verbose:
        grafter.report()

        if not dry_run:
            print("---------------------------------------------------")
            print("WARNING: Your active git branches may have changed!")
            print("---------------------------------------------------")

if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
