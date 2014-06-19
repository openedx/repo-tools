"""
Calculate pull requests opened and merged, by quarter.
"""

from __future__ import print_function

import collections
import datetime
import pprint

import dateutil.parser

from pulls import get_pulls
from repos import Repo


if 1:
    def date_bucket(date):
        """Compute the quarter for a date."""
        date += datetime.timedelta(days=180)    # to almost get to our fiscal year
        m = (date.month-1) // 3 + 1
        return "Y{:02d} Q{}".format(date.year % 100, m)
else:
    def date_bucket(date):
        """Compute the year and month for a date."""
        return "Y{:02d} M{:02d}".format(date.year % 100, date.month)

def get_all_repos():
    repos = [ r for r in Repo.from_yaml() if r.track_pulls ]

    def bucket_blank():
        return {
            "opened": {
                "internal": 0,
                "external": 0,
            },
            "merged": {
                "internal": 0,
                "external": 0,
            },
        }

    buckets = collections.defaultdict(bucket_blank)
    for repo in repos:
        get_bucket_data(buckets, repo.name)

    print("qrtr\topened internal\tmerged internal\topened external\tmerged external")
    for q in sorted(buckets.keys()):
        data = buckets[q]
        print("{}\t{}\t{}\t{}\t{}".format(q,
            data["opened"]["internal"],
            data["merged"]["internal"],
            data["opened"]["external"],
            data["merged"]["external"],
        ))

def get_bucket_data(buckets, repo_name):
    for pull in get_pulls(repo_name, state="all", pull_details="list", org=True):
        # print("{0[id]}: {0[combinedstate]} {0[intext]}".format(pull))
        created = dateutil.parser.parse(pull['created_at'])
        buckets[date_bucket(created)]["opened"][pull["intext"]] += 1
        if pull['combinedstate'] == "merged":
            merged = dateutil.parser.parse(pull['pull.merged_at'])
            buckets[date_bucket(merged)]["merged"][pull["intext"]] += 1

get_all_repos()
