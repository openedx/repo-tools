#!/usr/bin/env python

from __future__ import print_function

import argparse
import collections
from datetime import date, timedelta
import sys

import dateutil.parser

from pulls import get_pulls
from repos import Repo

def main(argv):
    parser = argparse.ArgumentParser(description="Summarize pull requests by organization.")
    parser.add_argument("--since", metavar="DAYS", type=int,
        help="Only consider pull requests closed in the past DAYS days"
    )

    args = parser.parse_args(argv[1:])

    since = None
    if args.since:
        since = date.today() - timedelta(days=args.since)

    repos = [ r for r in Repo.from_yaml() if r.track_pulls ]

    by_org = collections.defaultdict(list)

    for repo in repos:
        for pull in get_pulls(repo.name, state="closed", pull_details="list", org=True, since=since):
            if pull['intext'] == "internal":
                continue
            if pull['combinedstate'] != "merged":
                continue

            #merged = dateutil.parser.parse(pull['pull.merged_at'])
            by_org[pull['org']].append(pull)

    keys = sorted(by_org, key=lambda k: len(by_org[k]), reverse=True)
    for key in keys:
        print("{}: {}".format(key, len(by_org[key])))

    for pr in by_org['unsigned']:
        import pprint
        pprint.pprint(pr.obj)
        print()
        print()

if __name__ == "__main__":
    sys.exit(main(sys.argv))
