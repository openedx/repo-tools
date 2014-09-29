#!/usr/bin/env python
from __future__ import print_function

import argparse
import itertools
import sys
import yaml

from datetime import date, datetime, timedelta
from backports import statistics

import iso8601

from pulls import get_pulls
from repos import Repo

DEBUG = False


def get_all_orgs():
    with open("people.yaml") as people_yaml:
        mapping = yaml.load(people_yaml)

    orgs = set(data.get('institution', 'other') for data in mapping.values())
    orgs.add('unsigned')
    return orgs


def get_duration_data(durations, owner_repo="edx/edx-platform", since=None):
    """
    Update `durations`, a dict of dict of lists of pull requests.

    `durations` has four lists of data, where each list contains pull requests:
      internal open pull requests (all)
      external open pull requests (all)
      internal closed pull requests (since the `since` value)
      external closed pull requests (since the `since` value)

    These lists are organized into a dictionary that categorizes the lists
    by position and state.
    """
    open_issues_generator = itertools.izip(
        get_pulls(owner_repo, state="open", org=True),
        itertools.repeat("open")
    )
    closed_issues_generator = itertools.izip(
        get_pulls(owner_repo, state="closed", since=since, org=True),
        itertools.repeat("closed")
    )

    for issue, state in itertools.chain(open_issues_generator, closed_issues_generator):
        created_at = iso8601.parse_date(issue["created_at"]).replace(tzinfo=None)
        if state == "open":
            closed_at = datetime.utcnow()
        else:
            closed_at = iso8601.parse_date(issue["closed_at"]).replace(tzinfo=None)
        issue['duration'] = closed_at - created_at

        if DEBUG:
            print("{pr[id]}: {pr[intext]} {state}".format(
                pr=issue, state=state
            ), file=sys.stderr)

        durations[state][issue['intext']].append(issue)


def main(argv):
    global DEBUG

    parser = argparse.ArgumentParser(description="Summarize pull requests.")
    parser.add_argument("--since", metavar="DAYS", type=int, default=14,
        help="For closed issues, only include issues updated in the past DAYS days [%(default)d]"
    )
    parser.add_argument("--human", action="store_true",
        help="Human-readable output"
    )
    parser.add_argument("--org", action="store_true",
        help="Break down by organization"
    )
    parser.add_argument("--debug", action="store_true",
        help="Show debugging info"
    )
    args = parser.parse_args(argv[1:])

    DEBUG = args.debug

    since = None
    if args.since:
        since = date.today() - timedelta(days=args.since)

    if args.org:
        categories = sorted(get_all_orgs())
        def cat_filter(cat, pr):
            return pr['org'] == cat
    else:
        categories = ["all"]
        def cat_filter(cat, pr):
            return True

    durations = {
        "open": {
            "internal": [],
            "external": [],
        },
        "closed": {
            "internal": [],
            "external": [],
        }
    }

    repos = [ r for r in Repo.from_yaml() if r.track_pulls ]
    for repo in repos:
        get_duration_data(durations, repo.name, since)

    for linenum, cat in enumerate(categories):
        ss_friendly = []
        for position in ("external", "internal"):
            for state in ("open", "closed"):
                seconds = [p['duration'].total_seconds() for p in durations[state][position] if cat_filter(cat, p)]
                if seconds:
                    median_seconds = int(statistics.median(seconds))
                    median_duration = timedelta(seconds=median_seconds)
                else:
                    median_seconds = -1
                    median_duration = "no data"
                population = "all"
                if state == "closed" and since:
                    population = "since {date}".format(date=since)
                if args.human:
                    print("median {position} {state} ({population}): {duration}".format(
                        position=position, state=state, population=population,
                        duration=median_duration
                    ))
                else:
                    ss_friendly += [len(seconds), median_seconds]

        if ss_friendly:
            if linenum == 0:
                print("cat\twhen\trepos\teopen\teopenage\teclosed\teclosedage\tiopen\tiopenage\ticlosed\ticlosedage")
            ss_data = "\t".join(str(x) for x in ss_friendly)
            print("{}\t{:%m/%d/%Y}\t{}\t{}".format(cat, date.today(), len(repos), ss_data))

if __name__ == "__main__":
    main(sys.argv)
