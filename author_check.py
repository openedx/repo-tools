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
import re
import sys
from datetime import date

import colors
import github3
import requests
import yaml

from helpers import paginated_get


# Global data.

SHOW_UNCOMMITTING_AUTHORS = False   # This probably isn't worth mentioning.
GITHUB_USER = None
PERSONAL_ACCESS_TOKEN = None
REPO_INFO = {}
entry_to_github = None
people = None


# Make convenient print functions.

builtin_print = print

def print(msg=None):
    """Print in utf8, as God intended."""
    if msg is not None:
        builtin_print(unicode(msg).encode('utf8'))
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
    entries = paginated_get(contributors_url, auth=(GITHUB_USER, PERSONAL_ACCESS_TOKEN))

    actual_contributors = set(entry["login"].lower() for entry in entries)
    hidden_contributors = set((REPO_INFO.get(owner_repo) or {}).get("hidden-contributors", []))
    return actual_contributors | hidden_contributors

AUTHOR_ENTRY_RE = re.compile(r"""
    ^                   # start of line
    \s*                 # optional whitespace
    (?P<name>[^<]+)     # the "name" is all characters up until the first "<"
    \s*                 # maybe spaces separating name and email
    <(?P<email>[^>]+)>  # the "email" has "<" on the left and ">" on the right,
                        # and doesn't contain ">" in it
    \s*                 # optional whitespace
    $                   # end of line
    """, re.VERBOSE)


def get_name_from_authors_entry(entry):
    match = AUTHOR_ENTRY_RE.match(entry)
    if match:
        return match.group("name").strip()
    # if it doesn't match, assume the whole thing is just the name
    return entry.strip()


def authors_file_names(owner_repo, branch="master", filename="AUTHORS"):
    authors_url = AUTHORS_URL.format(
        owner_repo=owner_repo, branch=branch, filename=filename
    )
    r = requests.get(authors_url, auth=(GITHUB_USER, PERSONAL_ACCESS_TOKEN))
    if r.status_code == 404:
        return set()
    return set(
        get_name_from_authors_entry(line)
        for line in r.text.splitlines()
        if line and not line.isupper()
    )


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
    author_names = authors_file_names(owner_repo)

    if not author_names:
        print_red("AUTHORS FILE RETURNED EMPTY")

    if author_names:

        # who has contributed but isn't in the AUTHORS file or hasn't signed a CA

        for contributor in c:
            if contributor not in people:
                print_red("{} is a contributor but not in people file".format(contributor))
                all_clear = False
            else:
                if people[contributor]["name"] not in author_names:
                    print_yellow(u"{} <{}> {} is not in AUTHORS file".format(
                        people[contributor]["name"],
                        people[contributor].get("email", ""),
                        contributor
                    ))
                    all_clear = False
                if people[contributor].get("agreement") not in ["individual", "institution"]:
                    print_red(u"{} has contributed but not signed agreement".format(contributor))
                    all_clear = False

        # who is in the AUTHORS file but hasn't contributed

        for author in author_names:
            if author not in entry_to_github:
                print_red(u"{} is in AUTHORS but not in people file".format(author))
                all_clear = False
            elif SHOW_UNCOMMITTING_AUTHORS and entry_to_github[author] not in c:
                print_yellow(u"{} is in AUTHORS file but doesn't seem to have made a commit".format(author))
                all_clear = False

    else:
        print_yellow("No AUTHORS file")
        all_clear = False

    # who has a pull-request that we have't received a CA from

    not_in_people = defaultdict(set)
    no_agreement = defaultdict(set)
    expired = defaultdict(set)

    for pull in pull_requests(owner_repo):
        user_login = pull.user.login.lower()
        if user_login not in people:
            not_in_people[pull.user.login].add(str(pull.number))
        else:
            expires_on = people[user_login].get("expires_on", date.max)
            if expires_on < date.today():
                expired[pull.user.login].add(str(pull.number))

            if people[user_login].get("agreement") not in ["individual", "institution"]:
                no_agreement[pull.user.login].add(str(pull.number))

    print()

    for user, numbers in not_in_people.items():
        print_red(u"{} is not in people file [PR {}]".format(user, ", ".join(numbers)))
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
    if user_login not in people:
        print_red(u"{} is not in people file".format(pull.user.login))
    elif people[user_login].get("agreement") not in ["individual", "institution"]:
        print(u"{} has not signed agreement".format(pull.user.login))
    if pull.merged_by:
        print(u"merged by {}".format(pull.merged_by))


def check_user(username):
    username = username.lower()
    if username not in people:
        print_red(u"{} is not in people file".format(username))
    else:
        agreement = people[username]["agreement"]
        print(people[username].get("name", ""))
        expires_on = people[username].get("expires_on", date.max)
        if expires_on < date.today():
            print_red(u"{} used to have an agreement, but it is expired".format(username))
            return

        if agreement == "individual":
            print_green(u"{} has signed an individual agreement".format(username))
        elif agreement == "institution":
            institution = people[username].get("institution")
            msg = u"{} is covered by an institutional agreement".format(username)
            if institution:
                msg += u" with {}".format(institution)
            else:
                msg += u" (institution unknown)"
            print_green(msg)
        else:
            print_red(u"{} has not signed agreement".format(username))


def main(argv):
    global GITHUB_USER, PERSONAL_ACCESS_TOKEN, REPO_INFO
    global github, people, entry_to_github

    with open("auth.yaml") as auth_file:
        auth_info = yaml.load(auth_file)

        GITHUB_USER = auth_info["user"]
        PERSONAL_ACCESS_TOKEN = auth_info["token"]

    with open("repos.yaml") as repos_file:
        REPO_INFO = yaml.load(repos_file)

    with open("people.yaml") as people_file:
        people = yaml.load(people_file)
        people = {k.lower():v for k,v in people.items()}

    entry_to_github = {people[contributor]["name"]: contributor for contributor in people}

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
            try:
                check_repo(owner_repo)
            except Exception as e:
                print_red("Couldn't check repo {}: {}".format(owner_repo, e))

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
