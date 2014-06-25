#!/usr/bin/env python
from __future__ import print_function

import argparse
from datetime import date, datetime, timedelta
import itertools
from pprint import pprint
import sys

import yaml
import iso8601

from helpers import paginated_get, requests
from pulls import get_pulls
from repos import Repo


def get_internal():
    with open("people.yaml") as people_yaml:
        mapping = yaml.load(people_yaml)

    internal = { name: (info.get("institution", "unknown") == "edX") for name, info in mapping.iteritems() }
    return internal


def get_comment_data(repo, since, internal):
    pull_kwargs = dict(org=True, pull_details="get")
    open_issues = get_pulls(repo, state="open", **pull_kwargs)
    closed_issues = get_pulls(repo, state="closed", since=since, **pull_kwargs)

    for pull in itertools.chain(open_issues, closed_issues):
        #print("-"*80)
        #pprint(pull.obj)
        if pull['intext'] == "internal":
            continue

        users = set()
        for comment in paginated_get(pull['comments_url']):
            created_at = iso8601.parse_date(comment["created_at"]).replace(tzinfo=None)
            commenter = comment["user"]["login"]
            if created_at >= since and internal(commenter):
                if not users:
                    print(pull.format("{id} by {user.login}: {pull.changed_files} files, {pull.additions} lines added {pull.deletions} deleted"))
                    print(pull.format("  {title}"))
                    print(pull.format("  {url}"))
                users.add(commenter)
        if users:
            print("\n".join("    {}".format(user) for user in sorted(users)))


def main(argv):

    parser = argparse.ArgumentParser(description="Collect info about people commenting on pull requests")
    parser.add_argument("--since", metavar="DAYS", type=int, default=14,
        help="Include comments in this many days [%(default)d]"
    )
    parser.add_argument("--debug", action="store_true",
        help="Break down by organization"
    )
    args = parser.parse_args(argv[1:])

    since = None
    if args.since:
        since = datetime.now() - timedelta(days=args.since)

    internal = get_internal()
    repos = [ r for r in Repo.from_yaml() if r.track_pulls ]
    for repo in repos:
        get_comment_data(repo.name, since=since, internal=internal.get)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
