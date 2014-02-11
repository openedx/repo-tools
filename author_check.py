#!/usr/bin/env python

"""
./author_check.py <owner>/<repo>
audits the given repo

./author_check.py <owner>/<repo> <pull-request-number>
audits the given pull request

./author_check.py <user>
status of given user

./author_check.py
audits all repos in repos.yaml

requires an auth.yaml containing ``user`` and ``token`` to
use to access Github.
"""

from __future__ import print_function

from collections import defaultdict
import functools
import sys

import colors
import github3
import requests
import yaml


# Global data.

GITHUB_USER = None
PERSONAL_ACCESS_TOKEN = None
REPO_INFO = {}
entry_to_github = None
mapping = None


# Make convenient print functions.

builtin_print = print

def print(msg=None):
    """Print in utf8, as God intended."""
    if msg is not None:
        builtin_print(msg.encode('utf8'))
    else:
        builtin_print()


def print_in_color(color, msg):
    """Msg should be in color if going to a terminal."""
    if sys.stdout.isatty():
        msg = color(msg)
    print(msg)

print_red = functools.partial(print_in_color, colors.red)
print_yellow = functools.partial(print_in_color, colors.yellow)
print_green = functools.partial(print_in_color, colors.green)


# URL patterns

CONTRIBUTORS_URL = "https://api.github.com/repos/{owner_repo}/contributors"
AUTHORS_URL = "https://raw.github.com/{owner_repo}/{branch}/{filename}"


def contributors(owner_repo):
    """
    Returns a set of Github usernames who have contributed to the given repo.

    Usernames are lower-cased, since Github usernames are case-insensitive.

    """
    contributors_url = CONTRIBUTORS_URL.format(owner_repo=owner_repo)
    entries = requests.get(contributors_url, auth=(GITHUB_USER, PERSONAL_ACCESS_TOKEN)).json()

    return set(entry["login"].lower() for entry in entries)


def authors_file(owner_repo, branch="master", filename="AUTHORS"):
    authors_url = AUTHORS_URL.format(
        owner_repo=owner_repo, branch=branch, filename=filename
    )
    r = requests.get(authors_url, auth=(GITHUB_USER, PERSONAL_ACCESS_TOKEN))
    if r.status_code == 404:
        return None
    return set(line for line in r.text.splitlines() if "@" in line)


def pull_requests(owner_repo):
    owner, repo = owner_repo.split("/")
    return github.repository(owner, repo).iter_pulls()



def check_repo(owner_repo):

    all_clear = True

    print()
    print()
    print(owner_repo)
    print()

    c = contributors(owner_repo)
    a = authors_file(owner_repo)

    if a == set():
        print_red("AUTHORS FILE RETURNED EMPTY")

    if a is not None:

        # who has contributed but isn't in the AUTHORS file or hasn't signed a CA

        for contributor in c:
            if contributor not in mapping:
                print_red("{} is not in mapping file".format(contributor))
                all_clear = False
            else:
                if mapping[contributor]["authors_entry"] not in a:
                    print_yellow(u"{} {} is not in AUTHORS file".format(mapping[contributor]["authors_entry"], contributor))
                    all_clear = False
                if mapping[contributor].get("agreement") not in ["individual", "institution"]:
                    print_red(u"{} has contributed but not signed agreement".format(contributor))
                    all_clear = False

        # who is in the AUTHORS file but hasn't contributed

        for author in a:
            if author not in entry_to_github:
                print_red(u"{} is not in mapping file".format(author))
                all_clear = False
            elif entry_to_github[author] not in c:
                print_yellow(u"{} is in AUTHORS file but doesn't seem to have made a commit".format(author))
                all_clear = False

    else:
        print_yellow("No AUTHORS file")
        all_clear = False

    # who has a pull-request that we have't received a CA from

    not_in_mapping = defaultdict(set)
    no_agreement = defaultdict(set)

    for pull in pull_requests(owner_repo):
        user_login = pull.user.login.lower()
        if user_login not in mapping:
            not_in_mapping[pull.user.login].add(str(pull.number))
        else:
            if mapping[user_login].get("agreement") not in ["individual", "institution"]:
                no_agreement[pull.user.login].add(str(pull.number))

    print()

    for user, numbers in not_in_mapping.items():
        print_red(u"{} is not in mapping file [PR {}]".format(user, ", ".join(numbers)))
        all_clear = False
    for user, numbers in no_agreement.items():
        print_red(u"{} has not signed agreement [PR {}]".format(user, ", ".join(numbers)))
        all_clear = False

    if all_clear:
        print_green("ALL GOOD")


def check_pr(owner_repo, number):
    owner, repo = owner_repo.split("/")
    pull = github.repository(owner, repo).pull_request(number)
    print("[{}] {}".format(pull.state, pull.title))
    user_login = pull.user.login.lower()
    if user_login not in mapping:
        print_red(u"{} is not in mapping file".format(pull.user.login))
    elif mapping[user_login].get("agreement") not in ["individual", "institution"]:
        print(u"{} has not signed agreement".format(pull.user.login))
    if pull.merged_by:
        print(u"merged by {}".format(pull.merged_by))


def check_user(username):
    if username not in mapping:
        print_red(u"{} is not in mapping file".format(username))
    else:
        agreement = mapping[username]["agreement"]
        print(mapping[username].get("authors_entry", ""))
        if agreement == "individual":
            print_green(u"{} has signed an individual agreement".format(username))
        elif agreement == "institution":
            print_green(u"{} is covered by an institutional agreement".format(username))
        else:
            print_red(u"{} has not signed agreement".format(username))


def main(argv):
    global GITHUB_USER, PERSONAL_ACCESS_TOKEN, REPO_INFO
    global github, mapping, entry_to_github

    with open("auth.yaml") as auth_file:
        auth_info = yaml.load(auth_file)

        GITHUB_USER = auth_info["user"]
        PERSONAL_ACCESS_TOKEN = auth_info["token"]

    with open("repos.yaml") as repos_file:
        REPO_INFO = yaml.load(repos_file)

    with open("mapping.yaml") as mapping_file:
        mapping = yaml.load(mapping_file)
        mapping = {k.lower():v for k,v in mapping.items()}

    entry_to_github = {mapping[contributor]["authors_entry"]: contributor for contributor in mapping}

    github = github3.login(GITHUB_USER, password=PERSONAL_ACCESS_TOKEN)

    if len(argv) == 3:
        if "/" not in argv[1]:
            print_red("first arg must be of form owner/repo")
            return 1
        owner_repo = argv[1]
        number = argv[2]
        check_pr(owner_repo, number)
    elif len(argv) == 2:
        if "/" in argv[1]:
            owner_repo = argv[1]
            check_repo(owner_repo)
        else:
            check_user(argv[1])
    else:
        for owner_repo in sorted(REPO_INFO):
            check_repo(owner_repo)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
