#!/usr/bin/env python
"""
Calculate pull requests opened and merged, by quarter.
"""

from __future__ import print_function

import argparse
import collections
import datetime
import pprint
import sys

import dateutil.parser

from pulls import get_pulls
from repos import Repo


def date_bucket_quarter(date):
    """Compute the quarter for a date."""
    date += datetime.timedelta(days=180)    # to almost get to our fiscal year
    m = (date.month-1) // 3 + 1
    return "Y{:02d} Q{}".format(date.year % 100, m)

def date_bucket_month(date):
    """Compute the year and month for a date."""
    return "Y{:02d} M{:02d}".format(date.year % 100, date.month)

def date_bucket_week(date):
    """Compute the date of the Monday for a date, to bucket by weeks."""
    monday = date - datetime.timedelta(days=date.weekday())
    return "{:%Y-%m-%d}".format(monday)


def get_all_repos(date_bucket_fn):
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
        get_bucket_data(buckets, repo.name, date_bucket_fn)

    print("qrtr\topened internal\tmerged internal\topened external\tmerged external")
    for q in sorted(buckets.keys()):
        data = buckets[q]
        print("{}\t{}\t{}\t{}\t{}".format(q,
            data["opened"]["internal"],
            data["merged"]["internal"],
            data["opened"]["external"],
            data["merged"]["external"],
        ))

def get_bucket_data(buckets, repo_name, date_bucket_fn):
    for pull in get_pulls(repo_name, state="all", pull_details="list", org=True):
        # print("{0[id]}: {0[combinedstate]} {0[intext]}".format(pull))
        created = dateutil.parser.parse(pull['created_at'])
        buckets[date_bucket_fn(created)]["opened"][pull["intext"]] += 1
        if pull['combinedstate'] == "merged":
            merged = dateutil.parser.parse(pull['pull.merged_at'])
            buckets[date_bucket_fn(merged)]["merged"][pull["intext"]] += 1

def main(argv):
    parser = argparse.ArgumentParser(description="Summarize pull requests.")
    parser.add_argument("--monthly", action="store_true",
        help="Report on months instead of quarters"
    )
    parser.add_argument("--weekly", action="store_true",
        help="Report on weeks instead of quarters"
    )
    args = parser.parse_args(argv[1:])

    if args.monthly:
        date_bucket_fn = date_bucket_month
    elif args.weekly:
        date_bucket_fn = date_bucket_week
    else:
        date_bucket_fn = date_bucket_quarter

    get_all_repos(date_bucket_fn)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
