#!/usr/bin/env python
import collections
import datetime
import json
from pprint import pprint

import iso8601

from helpers import paginated_get
from pulls import get_pulls

"""
# pull ages
[
    {
        "team": "LMS",
        "total": 47,
        "internal": {
            "2+": [1234, 3434, 2232, 5345],
            "1-2": 12,
            "-week": 12,
            "-day": 6
        },
        "external": {
            ...
        }
    },
    {
        "team": "Studio",
        "total": 37,
        "internal": {...},
        "external": {...}
    },
    ...
}
"""

age_buckets = [
    (datetime.timedelta(days=1),    '<1 day'),
    (datetime.timedelta(days=7),    '<1 week'),
    (datetime.timedelta(days=14),   '1-2 weeks'),
    (datetime.timedelta.max,        '2+ weeks'),
]

def blank_sheet():
    { ab[1]:[] for ab in age_buckets }
    return {
        "total": 0,
        "internal": { ab[1]:[] for ab in age_buckets },
        "external": { ab[1]:[] for ab in age_buckets },
    }

def find_bucket(age):
    for delta, bucket in age_buckets:
        if age < delta:
            return bucket
    return "???"

LABELS_URL = "https://api.github.com/repos/{owner_repo}/labels"

def get_labels(owner_repo):
    url = LABELS_URL.format(owner_repo=owner_repo)
    return paginated_get(url)

def get_teams(owner_repo):
    for label in get_labels(owner_repo):
        if label["name"].startswith("waiting on "):
            yield label["name"][len("waiting on "):]

def show_wall():
    now = datetime.datetime.now()
    issues = get_pulls("edx/edx-platform", state="open")

    blocked_by = { team: blank_sheet() for team in get_teams("edx/edx-platform") }

    for issue in issues:
        issue.finish_loading()
        created_at = iso8601.parse_date(issue["created_at"]).replace(tzinfo=None)
        issue["age_bucket"] = bucket = find_bucket(now - created_at)
        issue["intext"] = intext = "external" if "osc" in issue['labels'] else "internal"
        for label in issue['labels']:
            if label == "osc":
                continue
            blocked_by[label][intext][bucket].append(issue["number"])
            blocked_by[label]["total"] += 1

    for team, data in blocked_by.iteritems():
        data["team"] = team

    #print(json.dumps(dict(blocked_by), indent=4))
    shame = sorted(blocked_by.values(), key=lambda d: d["total"], reverse=True)

    print(json.dumps(shame, indent=4))

    return

    shame = sorted(blocked_by.items(), key=lambda li: len(li[1]), reverse=True)
    print("team,external,internal,extlines,intlines")
    for label, issues in shame:
        internal, external = [0, 0], [0, 0]
        for iss in issues:
            lines = iss['pull.additions'] + iss['pull.deletions']
            stats = external if "osc" in iss['labels'] else internal
            stats[0] += 1
            stats[1] += lines
        print("{}\t{}\t{}\t{}\t{}".format(
            label, external[0], internal[0], external[1], internal[1]
        ))


if __name__ == "__main__":
    show_wall()
