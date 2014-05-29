#!/usr/bin/env python
import collections
import datetime
import json
from pprint import pprint

import iso8601

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

def get_labels(owner_repo):
    url = LABELS_URL.format(owner_repo=owner_repo)
    return paginated_get(url)

def get_teams(owner_repo):
    for label in get_labels(owner_repo):
        if label["name"].startswith("waiting on "):
            yield label["name"][len("waiting on "):]

def pull_summary(issue):
    """Create a jsonable summary of a pull request."""
    keys = [
        "number", "intext", "title", "labels", "org",
        "pull.html_url",
        "user.login",
        "user.html_url",
        "pull.created_at", "pull.updated_at",
        "created_bucket", "updated_bucket",
        "pull.comments", "pull.comments_url",
        "pull.commits", "pull.commits_url",
        "pull.additions", "pull.deletions",
        "pull.changed_files",
    ]
    summary = { k.replace("pull.", "").replace(".","_"):issue[k] for k in keys }
    return summary

def show_wall():
    issues = get_pulls("edx/edx-platform", state="open", org=True)

    blocked_by = { team: blank_sheet() for team in get_teams("edx/edx-platform") }
    pulls = {}

    for issue in issues:
        issue.finish_loading()
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
        for label in issue['labels']:
            if label == "osc":
                continue
            blocked_by[label][intext][bucket].append(issue["number"])
            blocked_by[label]["total"] += 1
        pulls[issue["number"]] = pull_summary(issue)

    for team, data in blocked_by.iteritems():
        data["team"] = team

    teams = sorted(
        blocked_by.values(),
        # waiting on author should be last.
        key=lambda d: (d["team"] != "author", d["total"]),
        reverse=True
    )

    all_data = {
        "buckets": [ab[1] for ab in age_buckets],
        "teams": teams,
        "pulls": pulls,
        "updated": NOW.isoformat(),
    }
    print(json.dumps(all_data, indent=4))

if __name__ == "__main__":
    show_wall()
