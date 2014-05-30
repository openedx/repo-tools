#!/usr/bin/env python

from __future__ import print_function

import datetime
import json

import iso8601
import yaml

from helpers import paginated_get
from pulls import get_pulls


age_buckets = [
    (datetime.timedelta.max,        '3+ weeks'),
    (datetime.timedelta(days=21),   '2-3 weeks'),
    (datetime.timedelta(days=14),   '1-2 weeks'),
    (datetime.timedelta(days=7),    '<1 week'),
]

NOW = datetime.datetime.now()

def blank_sheet():
    return {
        "total": 0,
        "internal": [[] for ab in age_buckets],
        "external": [[] for ab in age_buckets],
    }

def find_bucket(when):
    """Return the number of the age bucket for `when`."""
    age = NOW - when
    for i, (delta, bucket) in enumerate(reversed(age_buckets)):
        if age < delta:
            return len(age_buckets)-i-1
    assert False, "Should have found a bucket!"

LABELS_URL = "https://api.github.com/repos/{owner_repo}/labels"

def get_labels(repo):
    url = LABELS_URL.format(owner_repo=repo.name)
    return paginated_get(url)

def get_teams(repo):
    for label in get_labels(repo):
        if label["name"].startswith("waiting on "):
            yield label["name"][len("waiting on "):]

def pull_summary(issue):
    """Create a jsonable summary of a pull request."""
    keys = [
        "number", "title", "labels",
        "id", "repo", "intext", "org",
        "pull_request.html_url",
        "user.login",
        "user.html_url",
        "created_at", "updated_at",
        "created_bucket", "updated_bucket",
        #"pull.comments", "pull.comments_url",
        #"pull.commits", "pull.commits_url",
        #"pull.additions", "pull.deletions",
        #"pull.changed_files",
    ]
    summary = { k.replace("pull.", "").replace(".","_"):issue[k] for k in keys }
    return summary


class WallMaker(object):
    def __init__(self):
        self.blocked_by = None
        self.pulls = {}

    def show_wall(self, repos):

        for repo in repos:
            self.one_repo(repo)

        for team, data in self.blocked_by.iteritems():
            data["team"] = team

        teams = sorted(
            self.blocked_by.values(),
            # waiting on author should be last.
            key=lambda d: (d["team"] != "author", d["total"]),
            reverse=True
        )

        wall_data = {
            "buckets": [ab[1] for ab in age_buckets],
            "teams": teams,
            "pulls": self.pulls,
            "updated": NOW.isoformat(),
        }
        return wall_data

    def one_repo(self, repo):
        if self.blocked_by is None:
            self.blocked_by = { team: blank_sheet() for team in get_teams(repo) }

        issues = get_pulls(repo.name, state="open", org=True)
        for issue in issues:
            issue.finish_loading(pull_details=False)
            created_at = iso8601.parse_date(issue["created_at"]).replace(tzinfo=None)
            updated_at = iso8601.parse_date(issue["updated_at"]).replace(tzinfo=None)
            issue["created_bucket"] = bucket = find_bucket(created_at)
            issue["updated_bucket"] = find_bucket(updated_at)
            if "osc" in issue['labels']:
                intext = "external"
            elif issue['org'] == 'edX':
                intext = "internal"
            else:
                intext = "external"
            issue["intext"] = intext
            issue["id"] = issue_id = "{}.{}".format(repo.name, issue["number"])
            issue["repo"] = repo.nick
            for label in issue['labels']:
                if label == "osc":
                    continue
                if label not in self.blocked_by:
                    continue
                self.blocked_by[label][intext][bucket].append(issue_id)
                self.blocked_by[label]["total"] += 1
            self.pulls[issue_id] = pull_summary(issue)


class Repo(object):
    @classmethod
    def from_yaml(cls, filename="repos.yaml"):
        with open(filename) as yaml_file:
            all_repos = yaml.load(yaml_file)

        for name, data in all_repos.iteritems():
            yield cls(name, data)

    def __init__(self, name, data):
        self.name = name
        data = data or {}
        self.track_pulls = data.get("track-pulls", False)
        self.nick = data.get("nick", name)


def main():
    repos = [ r for r in Repo.from_yaml() if r.track_pulls ]
    wall_data = WallMaker().show_wall(repos)
    print(json.dumps(wall_data, indent=4))


if __name__ == "__main__":
    main()
