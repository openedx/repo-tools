#!/usr/bin/env python

from __future__ import print_function

import argparse
import collections
import datetime
import sys

from helpers import date_arg, make_timezone_aware
from repos import Repo
from webhookdb import get_pulls


def get_external_pulls(repo):
    """Produce a stream of external pull requests."""
    for issue in get_pulls(repo, state="all", org=True):
        if issue.intext == 'external':
            yield issue

def get_all_external_pulls():
    repos = [ r.name for r in Repo.from_yaml() if r.track_pulls ]
    for repo in repos:
        for pull in get_external_pulls(repo):
            yield pull

def get_pulls_in_window(start, end):
    for pull in get_all_external_pulls():
        if start < make_timezone_aware(pull.created_at) < end:
            yield pull

def get_contributor_counts(pulls):
    board = collections.Counter()
    for pull in pulls:
        board[pull.user_login] += 1

    return board

def main(argv):
    parser = argparse.ArgumentParser(description="Count external pull requests opened by person")
    parser.add_argument(
        "--start", type=date_arg,
        help="Date to start collecting, format is flexible: "
        "20141225, Dec/25/2014, 2014-12-25, etc"
    )
    parser.add_argument(
        "--end", type=date_arg,
        help="Date to end collecting, format is flexible: "
        "20141225, Dec/25/2014, 2014-12-25, etc"
    )

    args = parser.parse_args(argv[1:])

    if args.start is None:
        # Simplify the logic by always having a start date, but one so far back
        # that it is like having no start date.
        args.start = make_timezone_aware(datetime.datetime(2000, 1, 1))
    if args.end is None:
        # Simplify the logic by always having an end date, but one so far ahead
        # that it is like having no end date.
        args.end = make_timezone_aware(datetime.datetime(2040, 1, 1))

    pulls = get_pulls_in_window(args.start, args.end)
    board = get_contributor_counts(pulls)
    board = sorted(((v, k) for k,v in board.items()), reverse=True)
    for i, (count, user_login) in enumerate(board, start=1):
        print("{:4d}: {:4d} {}".format(i, count, user_login))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
