#!/usr/bin/env python
from __future__ import print_function

import argparse
import collections
import datetime
import more_itertools
import operator
import sys

import dateutil.parser

from helpers import paginated_get
from pulls import get_pulls

ISSUE_FMT = (
    "{number:5d:white:bold} {user.login:>17s:cyan} {comments:3d:red}"
    "  {title:.100s}"
    " {pull.commits}c{pull.changed_files}f"
    " {pull.additions:green}+{pull.deletions:red}-"
    " {combinedstate:pad:{combinedstatecolor}:negative}"
    " {updated_at:ago:white} {created_at:%b %d:yellow}"
    " {labels:spacejoin:pad:yellow:negative}"
)
COMMENT_FMT = "{:31}{user.login:cyan} {created_at:%b %d:yellow}  \t{body:oneline:.100s:white}"


def show_pulls(labels=None, show_comments=False, state="open", since=None, org=False):
    issues = get_pulls("edx/edx-platform", labels, state, since, org)

    category = None
    for index, issue in enumerate(issues):
        issue.finish_loading()
        if issue.get("org") != category:
            # new category! print category header
            category = issue["org"]
            print("-- {category} ----".format(category=category))

        if 0:
            import pprint
            pprint.pprint(issue.obj)
        print(issue.format(ISSUE_FMT))

        if show_comments:
            comments_url = URLObject(issue['comments_url'])
            comments_url = comments_url.set_query_param("sort", "created")
            comments_url = comments_url.set_query_param("direction", "desc")
            comments = paginated_get(comments_url)
            last_five_comments = reversed(more_itertools.take(5, comments))
            for comment in last_five_comments:
                print(comment.format(COMMENT_FMT))

    # index is now set to the total number of pull requests
    print()
    print("{num} pull requests".format(num=index+1))


if 0:
    """
    db.prs.find({  created_at: {   $gte: "2014-01-01T00:00:00.000Z",   $lt: "2014-04-01T00:00:00.000Z"  } }).count()
    db.prs.find({  created_at: {   $gte: "2014-04-01T00:00:00.000Z",   $lt: "2014-07-01T00:00:00.000Z"  } }).count()
    db.prs.find({ "pull.merged": true, "pull.merged_at": {   $gte: "2014-04-01T00:00:00.000Z",   $lt: "2014-07-01T00:00:00.000Z"  } }).count()
    db.prs.find({ "pull.merged": true, "pull.merged_at": {   $gte: "2014-01-01T00:00:00.000Z",   $lt: "2014-04-01T00:00:00.000Z"  } }).count()
    """

    from pymongo import MongoClient
    def insert_pulls(labels=None, state="open", since=None, org=False):
        mongo_client = MongoClient()
        mongo_collection = mongo_client.prs.prs

        issues = get_pulls("edx/edx-platform", labels, state, since, org)
        for issue in issues:
            mongo_collection.insert(issue)


if 0:
    def yearmonth(d):
        return dateutil.parser.parse(d).strftime("%Y%m")

    def show_pulls(labels=None, show_comments=False, state="open", since=None, org=False):
        months = collections.defaultdict(lambda: {'opened': 0, 'merged': 0})
        issues = get_pulls("edx/edx-platform", labels, state, since, org)
        for issue in issues:
            issue.finish_loading()
            months[yearmonth(issue['created_at'])]['opened'] += 1
            if issue['pull.merged']:
                months[yearmonth(issue['pull.merged_at'])]['merged'] += 1

        print(months)
        for ym, data in sorted(months.items()):
            print("{ym},{data[opened]},{data[merged]}".format(ym=ym, data=data))


def main(argv):
    parser = argparse.ArgumentParser(description="Summarize pull requests.")
    parser.add_argument("-a", "--all-labels", action='store_true',
        help="Show all open pull requests, else only open-source",
        )
    parser.add_argument("--closed", action='store_true',
        help="Include closed pull requests",
        )
    parser.add_argument("--comments", dest="show_comments", action='store_true',
        help="Also show 5 most recent comments",
        )
    parser.add_argument("--debug",
        help="See what's going on.  DEBUG=http or json are fun.",
        )
    parser.add_argument("--org", action='store_true',
        help="Include and sort by affiliation",
        )
    parser.add_argument("--since", metavar="DAYS", type=int,
        help="Include pull requests active in the last DAYS days.",
        )

    args = parser.parse_args(argv[1:])

    labels = []
    if not args.all_labels:
        labels.append("open-source-contribution")

    if args.closed:
        state = "all"
    else:
        state = "open"

    since = None
    if args.since:
        since = datetime.datetime.now() - datetime.timedelta(days=args.since)

    show_pulls(
        labels=labels,
        show_comments=args.show_comments,
        state=state,
        since=since,
        org=args.org,
    )


if __name__ == "__main__":
    main(sys.argv)
