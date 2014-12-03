#!/usr/bin/env python
"""
Calculate pull requests opened and merged, by quarter.
"""

from __future__ import print_function

import argparse
import collections
import datetime
import itertools
import pprint
import sys

import dateutil.parser

from helpers import date_arg, make_timezone_aware
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


def get_all_repos(date_bucket_fn, start, by_size=False):
    repos = [ r for r in Repo.from_yaml() if r.track_pulls ]

    dimensions = [["opened", "merged"], ["internal", "external"]]
    if by_size:
        dimensions.append(["small", "large"])

    keys = [" ".join(prod) for prod in itertools.product(*dimensions)]
    bucket_blank = dict.fromkeys(keys, 0)

    buckets = collections.defaultdict(lambda: dict(bucket_blank))
    for repo in repos:
        get_bucket_data(buckets, repo.name, date_bucket_fn, start=start, by_size=by_size)

    print("timespan\t" + "\t".join(keys))
    for q in sorted(buckets.keys()):
        data = buckets[q]
        print("{}\t{}".format(q, "\t".join(str(data[k]) for k in keys)))

def get_bucket_data(buckets, repo_name, date_bucket_fn, start, by_size=False):
    print(repo_name)
    pull_details = "all" if by_size else "list"
    for pull in get_pulls(repo_name, state="all", pull_details=pull_details, org=True):
        # print("{0[id]}: {0[combinedstate]} {0[intext]}".format(pull))
        if by_size:
            size = " " + size_of_pull(pull)
        else:
            size = ""
        intext = pull["intext"]
        created = dateutil.parser.parse(pull['created_at'])
        if created >= start:
            buckets[date_bucket_fn(created)]["opened " + intext + size] += 1
        if pull['combinedstate'] == "merged":
            merged = dateutil.parser.parse(pull['pull.merged_at'])
            if merged >= start:
                buckets[date_bucket_fn(merged)]["merged " + intext + size] += 1

def size_of_pull(pull):
    """Return a size (small/large) for the pull.

    This is based on a number of criteria, with wild-ass guesses about the
    dividing line between large and small.  Don't read too much into this
    distinction.

    Returns "small" or "large".

    """
    limits = {
        'pull.additions': 30,
        'pull.changed_files': 5,
        'pull.comments': 10,
        'pull.commits': 3,
        'pull.deletions': 30,
        'pull.review_comments': 10,
    }
    for attr, limit in limits.iteritems():
        if pull[attr] > limit:
            return "large"
    return "small"

def main(argv):
    parser = argparse.ArgumentParser(description="Summarize pull requests.")
    parser.add_argument("--monthly", action="store_true",
        help="Report on months instead of quarters"
    )
    parser.add_argument("--weekly", action="store_true",
        help="Report on weeks instead of quarters"
    )
    parser.add_argument("--by-size", action="store_true",
        help="Include a breakdown by small/large, "
                "which is WILDLY arbitrary, "
                "and a poor predicter of either effort or impact."
    )
    parser.add_argument("--start", type=date_arg,
        help="Date to start collecting, format is flexible: "
        "20141225, Dec/25/2014, 2014-12-25, etc"
    )
    args = parser.parse_args(argv[1:])

    if args.monthly:
        date_bucket_fn = date_bucket_month
    elif args.weekly:
        date_bucket_fn = date_bucket_week
    else:
        date_bucket_fn = date_bucket_quarter

    if args.start is None:
        # Simplify the logic by always having a start date, but one so far back
        # that it is like having no start date.
        args.start = make_timezone_aware(datetime.datetime(2000, 1, 1))

    get_all_repos(date_bucket_fn, by_size=args.by_size, start=args.start)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
