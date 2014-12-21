#!/usr/bin/env python
"""Count the number of unique contributors in a 90-day sliding window."""

from __future__ import print_function

import collections
import datetime

import iso8601

from helpers import requests
from webhookdb import get_pulls
from repos import Repo


def get_opened_pulls(repo):
    """Produce a stream of pull requests."""
    for issue in get_pulls(repo, state="all", org=True):
        if issue.intext == 'external':
            yield issue

Summary = collections.namedtuple("Summary", "id, user, created")

def get_summaries_from_repos(repos):
    """Make a stream of summaries from a list of repos."""
    for repo in repos:
        for pull in get_opened_pulls(repo):
            yield Summary(pull.id, pull.user_login, pull.created_at)

def date_range(start, end, step):
    """Like range(), but for other types, like dates."""
    when = start
    while when < end:
        yield when
        when += step

def sliding_window(seq, key, width, step):
    """Produce a sequence of sliding windows on the data in `seq`.

    `seq` is a sequence of data.  `key` is a function that produces a date from
    an item in the sequence.  `width` is a timedelta specifying the width of the
    window, and `step` is a timedelta specifying a step between successive starts
    of the window.

    The result is a sequence of pairs: (date, [items]), where date is the start
    date of each window, and [items] are the items whose date falls within the
    window.

    """
    items = sorted(seq, key=key)
    start = min(key(item) for item in items)
    end = max(key(item) for item in items) - width

    for when in date_range(start, end, step):
        window_end = when + width
        in_window = [item for item in items if when <= key(item) < window_end]
        yield when, in_window

def unique_authors(repos):
    """Produce a sequence of pairs: (date, num-contributors)."""
    pulls = get_summaries_from_repos(repos)
    key = lambda s: s.created
    width = datetime.timedelta(days=90)
    step = datetime.timedelta(days=7)

    for when, window in sliding_window(pulls, key=key, width=width, step=step):
        num_authors = len(set(p.user for p in window))
        yield (when+width, num_authors)

def main():
    # Yes, hard-coded start date.
    start = datetime.datetime(2013, 6, 5)
    repos = [ r.name for r in Repo.from_yaml() if r.track_pulls ]
    for when, num_authors in unique_authors(repos):
        if when < start:
            continue
        print("{0:%Y-%m-%d}\t{1}".format(when, num_authors))

if __name__ == '__main__':
    main()
