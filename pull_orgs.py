#!/usr/bin/env python

from __future__ import print_function

import argparse
import collections
from datetime import datetime, timedelta
import sys

from helpers import date_arg, make_timezone_aware
from webhookdb import get_pulls
from repos import Repo


def main(argv):
    parser = argparse.ArgumentParser(description="Summarize pull requests by organization.")
    parser.add_argument(
        "--since", metavar="DAYS", type=int,
        help="Only consider pull requests closed in the past DAYS days"
    )
    parser.add_argument(
        "--start", type=date_arg,
        help="Date to start collecting, format is flexible: "
        "20141225, Dec/25/2014, 2014-12-25, etc"
    )
    parser.add_argument(
        "--end", type=date_arg,
        help="Date to end collecting, format is flexible: "
        "25/Dec/2014, 12/25/2014, 2014-12-25, etc"
    )

    args = parser.parse_args(argv[1:])

    since = None
    if args.since:
        since = make_timezone_aware(datetime.today() - timedelta(days=args.since))
    if args.start:
        if since is not None:
            raise Exception("Can't use --since and --start")
        since = args.start

    repos = [ r for r in Repo.from_yaml() if r.track_pulls ]

    by_org = collections.defaultdict(list)

    for repo in repos:
        for pull in get_pulls(repo.name, state="closed", pull_details="list", org=True, since=since):
            # We only want external pull requests.
            if pull.intext != "external":
                continue
            # We only want merged pull requests.
            if pull.combinedstate != "merged":
                continue
            # Pull requests can be recently modified even if they were merged
            # long ago, so only take things merged since our since date.
            merged = make_timezone_aware(pull.merged_at)
            if merged < since:
                continue

            if args.end is not None:
                # We don't want to count things merged after our end date.
                if merged >= args.end:
                    continue

            pull.repo = repo.nick
            by_org[pull.org].append(pull)

    keys = sorted(by_org, key=lambda k: len(by_org[k]), reverse=True)
    for key in keys:
        print("{}: {}".format(key, len(by_org[key])))

    fmt = "{pull.repo:4s} {pull.number:5d} {pull.user_login:>17s} {pull.title}"

    for key in keys:
        print("\n-- {} -------".format(key))
        for pull in by_org[key]:
            print(fmt.format(pull=pull))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
