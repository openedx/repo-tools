#!/usr/bin/env python
"""
Calculate interal and external pull requests both opened and merged,
by quarter, month, or week.

Returns the raw # of PRs opened, and the raw # merged, per time increment.
For example, if a PR is opened in July and merged in August, it is counted as
opened in July, and merged in August.
"""

from __future__ import print_function

import argparse
import collections
import datetime
import itertools
import re
import sys

from helpers import date_arg, make_timezone_aware
from repos import Repo


def date_bucket_quarter(date):
    """Compute the quarter for a date."""
    date += datetime.timedelta(days=180)    # to almost get to our fiscal year
    quarter = (date.month-1) // 3 + 1
    return "Y{:02d} Q{}".format(date.year % 100, quarter)

def date_bucket_month(date):
    """Compute the year and month for a date."""
    return "Y{:02d} M{:02d}".format(date.year % 100, date.month)

def date_bucket_week(date):
    """Compute the date of the Monday for a date, to bucket by weeks."""
    monday = date - datetime.timedelta(days=date.weekday())
    return "{:%Y-%m-%d}".format(monday)


def get_all_repos(date_bucket_fn, start, by_size=False, lines=False, closed=False):
    repos = [r for r in Repo.from_yaml() if r.track_pulls]

    dimensions = []
    if closed:
        dimensions.append(["opened", "merged", "closed"])
    else:
        dimensions.append(["opened", "merged"])
    dimensions.append(["internal", "external"])
    if by_size:
        dimensions.append(["small", "large"])

    keys = [" ".join(prod) for prod in itertools.product(*dimensions)]
    bucket_blank = dict.fromkeys(keys, 0)

    buckets = collections.defaultdict(lambda: dict(bucket_blank))
    for repo in repos:
        get_bucket_data(buckets, repo.name, date_bucket_fn, start=start, by_size=by_size, lines=lines, closed=closed)

    print("timespan\t" + "\t".join(keys))
    for time_period in sorted(buckets.keys()):
        data = buckets[time_period]
        print("{}\t{}".format(time_period, "\t".join(str(data[k]) for k in keys)))

def get_bucket_data(buckets, repo_name, date_bucket_fn, start, by_size=False, lines=False, closed=False):
    print(repo_name)
    pull_details = "all" if (by_size or lines) else "list"
    for pull in get_pulls(repo_name, state="all", pull_details=pull_details, org=True):
        # print("{0.id}: {0.combinedstate} {0.intext}".format(pull))

        ignore_ref = "(^release$|^rc/)"
        if re.search(ignore_ref, pull.base_ref):
            #print("Ignoring pull #{0.number}: {0.title}".format(pull))
            continue

        if by_size:
            size = " " + size_of_pull(pull)
        else:
            size = ""
        intext = pull.intext

        if lines:
            increment = lines_in_pull(pull)
        else:
            increment = 1

        created = make_timezone_aware(pull.created_at)
        if created >= start:
            buckets[date_bucket_fn(created)]["opened " + intext + size] += increment

        if pull.combinedstate == "merged":
            merged = make_timezone_aware(pull.merged_at)
            if merged >= start:
                buckets[date_bucket_fn(merged)]["merged " + intext + size] += increment
        elif closed and pull.combinedstate == "closed":
            closed = make_timezone_aware(pull.closed_at)
            buckets[date_bucket_fn(closed)]["closed " + intext + size] += increment

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

def lines_in_pull(pull):
    """Return a line count for the pull request.

    To consider both added and deleted, we add them together, but discount the
    deleted count, on the theory that adding a line is harder than deleting a
    line (*waves hands very broadly*).

    """
    ignore = r"(/vendor/)|(conf/locale)|(static/fonts)|(test/data/uploads)"
    lines = 0
    files = pull.get_files()
    for f in files:
        if re.search(ignore, f.filename):
            #print("Ignoring file {}".format(f.filename))
            continue
        lines += f.additions + f.deletions//5
    if pull.combinedstate == "merged" and lines > 2000:
        print("*** Large pull: {lines:-6d} lines, {pr.created_at} {pr.number:-4d}: {pr.title}".format(lines=lines, pr=pull))
    return lines

def main(argv):
    parser = argparse.ArgumentParser(description="Calculate internal & external pull requests, both opened & merged, by quarter.")
    parser.add_argument(
        "--monthly", action="store_true",
        help="Report on months instead of quarters"
    )
    parser.add_argument(
        "--weekly", action="store_true",
        help="Report on weeks instead of quarters"
    )
    parser.add_argument(
        "--by-size", action="store_true",
        help="Include a breakdown by small/large, which is WILDLY arbitrary, "
            "and a poor predicter of either effort or impact."
    )
    parser.add_argument(
        "--lines", action="store_true",
        help="Count the number of lines changed instead of number of pull requests"
    )
    parser.add_argument(
        "--start", type=date_arg,
        help="Date to start collecting, format is flexible: "
        "20141225, Dec/25/2014, 2014-12-25, etc"
    )
    parser.add_argument(
        "--db", action="store_true",
        help="Use WebhookDB instead of GitHub API"
    )
    parser.add_argument(
        "--closed", action="store_true",
        help="Include closed pull requests also"
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

    global get_pulls
    if args.db:
        from webhookdb import get_pulls
    else:
        from githubapi import get_pulls

    get_all_repos(date_bucket_fn, by_size=args.by_size, start=args.start, lines=args.lines, closed=args.closed)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
