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


from collections import defaultdict
import sys

from colors import red, yellow, green
from github3 import login
import requests
import yaml

with open("auth.yaml") as auth_file:
    auth_info = yaml.load(auth_file)

    GITHUB_USER = auth_info["user"]
    PERSONAL_ACCESS_TOKEN = auth_info["token"]

with open("repos.yaml") as repos_file:
    REPO_LIST = yaml.load(repos_file)


# URL patterns

CONTRIBUTORS_URL = "https://api.github.com/repos/{owner}/{repo}/contributors"
AUTHORS_URL = "https://raw.github.com/{owner}/{repo}/{branch}/{filename}"

gh = login(GITHUB_USER, password=PERSONAL_ACCESS_TOKEN)

def contributors(owner, repo):
    """
    returns a set of github usernames who have contributed to the given repo.
    """
    contributors_url = CONTRIBUTORS_URL.format(owner=owner, repo=repo)
    entries = requests.get(contributors_url, auth=(GITHUB_USER, PERSONAL_ACCESS_TOKEN)).json()
    
    return set(entry["login"] for entry in entries)


def authors_file(owner, repo, branch="master", filename="AUTHORS"):
    authors_url = AUTHORS_URL.format(
        owner=owner, repo=repo, branch=branch, filename=filename
    )
    r = requests.get(authors_url, auth=(GITHUB_USER, PERSONAL_ACCESS_TOKEN))
    if r.status_code == 404:
        return None
    return set(line for line in r.text.split("\n") if "@" in line)


def pull_requests(owner, repo):
    return gh.repository(owner, repo).iter_pulls()


with open("mapping.yaml") as mapping_file:
    mapping = yaml.load(mapping_file)

entry_to_github = {mapping[contributor]["authors_entry"]: contributor for contributor in mapping}


def check_repo(owner, repo):
    
    all_clear = True
    
    print
    print
    print "{}/{}".format(owner, repo)
    print
    
    c = contributors(owner, repo)
    a = authors_file(owner, repo)
    
    if a == set():
        print red("AUTHORS FILE RETURNED EMPTY")
    
    if a is not None:
    
        # who has contributed but isn't in the AUTHORS file or hasn't signed a CA

        for contributor in c:
            if contributor not in mapping:
                print red("{} is not in mapping file".format(contributor))
                all_clear = False
            else:
                if mapping[contributor]["authors_entry"] not in a:
                    print yellow(u"{} {} is not in AUTHORS file".format(mapping[contributor]["authors_entry"], contributor))
                    all_clear = False
                if mapping[contributor].get("agreement") not in ["individual", "institution"]:
                    print red(u"{} has contributed but not signed agreement".format(contributor))
                    all_clear = False
        
        # who is in the AUTHORS file but hasn't contributed
        
        for author in a:
            if author not in entry_to_github:
                print red(u"{} is not in mapping file".format(author))
                all_clear = False
            elif entry_to_github[author] not in c:
                print yellow(u"{} is in AUTHORS file but doesn't seem to have made a commit".format(author))
                all_clear = False
    
    else:
        print yellow("No AUTHORS file")
        all_clear = False
    
    # who has a pull-request that we have't received a CA from
    
    not_in_mapping = defaultdict(set)
    no_agreement = defaultdict(set)
    
    for pull in pull_requests(owner, repo):
        if pull.user.login not in mapping:
            not_in_mapping[pull.user.login].add(str(pull.number))
        else:
            if mapping[pull.user.login].get("agreement") not in ["individual", "institution"]:
                no_agreement[pull.user.login].add(str(pull.number))
    
    print
    
    for user, numbers in not_in_mapping.items():
        print red(u"{} is not in mapping file [PR {}]".format(user, ", ".join(numbers)))
        all_clear = False
    for user, numbers in no_agreement.items():
        print red(u"{} has not signed agreement [PR {}]".format(user, ", ".join(numbers)))
        all_clear = False
    
    if all_clear:
        print green("ALL GOOD")


def check_pr(owner, repo, number):
    pull = gh.repository(owner, repo).pull_request(number)
    print "[{}] {}".format(pull.state, pull.title)
    if pull.user.login not in mapping:
        print red(u"{} is not in mapping file".format(pull.user.login))
    elif mapping[pull.user.login].get("agreement") not in ["individual", "institution"]:
        print u"{} has not signed agreement".format(pull.user.login)
    if pull.merged_by:
        print u"merged by {}".format(pull.merged_by)


def check_user(username):
    if username not in mapping:
        print red(u"{} is not in mapping file".format(username))
    else:
        agreement = mapping[username]["agreement"]
        print mapping[username].get("authors_entry", "")
        if agreement == "individual":
            print green(u"{} has signed an individual agreement".format(username))
        elif agreement == "institution":
            print green(u"{} is covered by an institutional agreement".format(username))
        else:
            print red(u"{} has not signed agreement".format(username))


if len(sys.argv) == 3:
    if "/" not in sys.argv[1]:
        print red("first arg must be of form owner/repo")
        sys.exit(1)
    owner, repo = sys.argv[1].split("/")
    number = sys.argv[2]
    check_pr(owner, repo, number)
elif len(sys.argv) == 2:
    if "/" in sys.argv[1]:
        owner, repo = sys.argv[1].split("/")
        check_repo(owner, repo)
    else:
        check_user(sys.argv[1])
else:
    for repo in REPO_LIST:
        check_repo(*repo.split("/"))


print
print
