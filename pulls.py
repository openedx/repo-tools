#!/usr/bin/env python
from __future__ import print_function

import argparse
import collections
import datetime
import more_itertools
import operator
import sys

import dateutil.parser
from pymongo import MongoClient
import requests
from urlobject import URLObject
import yaml

import jreport
from jreport.util import paginated_get

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


class JPullRequest(jreport.JObj):
    def __init__(self, issue_data, org_fn=None):
        super(JPullRequest, self).__init__(issue_data)
        if org_fn:
            self['org'] = org_fn(self)

    def finish_loading(self):
        self['pull'] = requests.get(self._pr_url).json()

        if self['state'] == 'open':
            self['combinedstate'] = 'open'
            self['combinedstatecolor'] = 'green'
        elif self['pull.merged']:
            self['combinedstate'] = 'merged'
            self['combinedstatecolor'] = 'blue'
        else:
            self['combinedstate'] = 'closed'
            self['combinedstatecolor'] = 'red'

        self['labels'] = [self.short_label(l['name']) for l in self['labels']]

    def short_label(self, lname):
        if lname == "open-source-contribution":
            return "osc"
        if lname.startswith("waiting on "):
            return lname[len("waiting on "):]
        return lname

    @classmethod
    def from_json(cls, issues_data, org_fn=None):
        for issue_data in issues_data:
            issue = cls(issue_data, org_fn)
            pr_url = issue.get('pull_request', {}).get('url')
            if not pr_url:
                continue
            issue._pr_url = pr_url

            yield issue


def get_pulls(labels=None, state="open", since=None, org=False):
    url = URLObject("https://api.github.com/repos/edx/edx-platform/issues")
    if labels:
        url = url.set_query_param('labels', ",".join(labels))
    if since:
        url = url.set_query_param('since', since.isoformat())
    if state:
        url = url.set_query_param('state', state)
    url = url.set_query_param('sort', 'updated')

    org_fn = None
    if org:
        try:
            with open("mapping.yaml") as fmapping:
                user_mapping = yaml.load(fmapping)
            def_org = "other"
        except IOError:
            user_mapping = {}
            def_org = "---"

        def org_fn(issue):
            return user_mapping.get(issue["user.login"], {}).get("institution", def_org)

    issues = JPullRequest.from_json(paginated_get(url), org_fn)
    if org:
        issues = sorted(issues, key=operator.itemgetter("org"))

    return issues


def show_pulls(jrep, labels=None, show_comments=False, state="open", since=None, org=False):
    issues = get_pulls(labels, state, since, org)

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

    def insert_pulls(labels=None, state="open", since=None, org=False):
        mongo_client = MongoClient()
        mongo_collection = mongo_client.prs.prs

        issues = get_pulls(labels, state, since, org)
        for issue in issues:
            mongo_collection.insert(issue)


if 0:
    def yearmonth(d):
        return dateutil.parser.parse(d).strftime("%Y%m")

    def show_pulls(jrep, labels=None, show_comments=False, state="open", since=None, org=False):
        months = collections.defaultdict(lambda: {'opened': 0, 'merged': 0})
        issues = get_pulls(labels, state, since, org)
        for issue in issues:
            issue.finish_loading()
            months[yearmonth(issue['created_at'])]['opened'] += 1
            if issue['pull.merged']:
                months[yearmonth(issue['pull.merged_at'])]['merged'] += 1

        print(months)
        for ym, data in sorted(months.items()):
            print("{ym},{data[opened]},{data[merged]}".format(ym=ym, data=data))

if 0:
    # The wall of shame
    def show_pulls(jrep, labels=None, show_comments=False, state="open", since=None, org=False):
        issues = get_pulls(state="open")
        blocked_by = collections.defaultdict(list)
        for issue in issues:
            issue.finish_loading()
            for label in issue['labels']:
                if label == "osc":
                    continue
                blocked_by[label].append(issue)

        shame = sorted(blocked_by.items(), key=lambda li: len(li[1]), reverse=True)
        print("team,external,internal,extlines,intlines")
        for label, issues in shame:
            internal, external = [0, 0], [0, 0]
            for iss in issues:
                lines = iss['pull.additions'] + iss['pull.deletions']
                stats = external if "osc" in iss['labels'] else internal
                stats[0] += 1
                stats[1] += lines
            print("{}\t{}\t{}\t{}\t{}".format(
                label, external[0], internal[0], external[1], internal[1]
            ))

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

    jrep = jreport.JReport(debug=args.debug)
    show_pulls(
        jrep,
        labels=labels,
        show_comments=args.show_comments,
        state=state,
        since=since,
        org=args.org,
    )


if __name__ == "__main__":
    main(sys.argv)
