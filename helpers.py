"""Helpers for various things."""

from __future__ import print_function

import os
import pprint
import re
import sys

import requests as real_requests

from urlobject import URLObject

try:
    from cachecontrol import CacheControlAdapter
    from cachecontrol.caches import FileCache
except ImportError:
    CacheControlAdapter = None

import dateutil.parser
import dateutil.tz


def date_arg(s):
    """An argument parser for dates."""
    return make_timezone_aware(dateutil.parser.parse(s))

def make_timezone_aware(dt):
    """Make a datetime timezone-aware."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=dateutil.tz.tzutc())
    return dt


class WrappedRequests(object):
    """A helper wrapper around requests.

    Provides uniform authentication and logging.
    """

    def __init__(self):
        self._session = None
        self.all_requests = None

    @property
    def session(self):
        if self._session is None:
            self._session = real_requests.Session()
            if CacheControlAdapter:
                adapter = CacheControlAdapter(cache=FileCache(".webcache"))
                self._session.mount("http://", adapter)
                self._session.mount("https://", adapter)
                print("Caching to .webcache")
        return self._session

    def record_request(self, method, url, args, kwargs):
        if 0:
            print("{} {}".format(method, url))
        if self.all_requests is None:
            return
        self.all_requests.append(
            "{}: {} {} {}".format(
                method, url, args if args else "", kwargs if kwargs else ""
            ).rstrip()
        )

    def _kwargs(self, url, kwargs):
        """Adjust the kwargs for a request."""
        if "auth" not in kwargs:
            # For Heroku, get github credentials from environment vars.
            if url.startswith("https://api.github.com"):
                user_name = os.environ.get("GITHUB_API_USER")
                token = os.environ.get("GITHUB_API_TOKEN")
                if user_name and token:
                    kwargs["auth"] = (user_name, token)
        return kwargs

    def get(self, url, *args, **kwargs):
        self.record_request("GET", url, args, kwargs)
        response = self.session.get(url, *args, **self._kwargs(url, kwargs))
        if 0:
            # Useful for diagnosing caching issues with the GitHub API.
            print("request:")
            pprint.pprint(dict(response.request.headers))
            if response.from_cache:
                info = "cached"
            else:
                info = "{} left".format(response.headers["X-RateLimit-Remaining"])
                print("headers:")
                pprint.pprint(dict(response.headers))
            print("GET {}: {}".format(url, info))
        return response

    def post(self, url, *args, **kwargs):
        self.record_request("POST", url, args, kwargs)
        return self.session.post(url, *args, **self._kwargs(url, kwargs))


# Now we can use requests as usual, or even import it from this module.
requests = WrappedRequests()


def paginated_get(url, limit=None, debug=False, **kwargs):
    """
    Retrieve all objects from a paginated API.

    Assumes that the pagination is specified in the "link" header, like
    Github's v3 API.

    The `limit` describes how many results you'd like returned.  You might get
    more than this, but you won't make more requests to the server once this
    limit has been exceeded.  For example, paginating by 100, if you set a
    limit of 250, three requests will be made, and you'll get 300 objects.

    """
    url = URLObject(url).set_query_param('per_page', '100')
    limit = limit or 999999999
    returned = 0
    while url:
        resp = requests.get(url, **kwargs)
        result = resp.json()
        if not resp.ok:
            raise real_requests.exceptions.RequestException(result["message"])
        if debug:
            pprint.pprint(result, stream=sys.stderr)
        for item in result:
            yield item
            returned += 1
        url = None
        if "link" in resp.headers and returned < limit:
            match = re.search(r'<(?P<url>[^>]+)>; rel="next"', resp.headers["link"])
            if match:
                url = match.group('url')


def only_once(func):
    """Simple caching decorator for a no-argument function to only be called once."""
    def decorator():
        if not hasattr(func, "only_once_return"):
            ret = func()
            func.only_once_return = ret
        return func.only_once_return
    return decorator


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


def print_repo_output(keys, buckets):
    """
    Given a list of dimension keys and the bucket data, print
    it nicely to stdout (used in monthly_pr_stats and pull_quarters)
    """
    print("timespan\t" + "\t".join(keys))
    for time_period in sorted(buckets.keys()):
        data = buckets[time_period]
        print("{}\t{}".format(time_period, "\t".join(str(data[k]) for k in keys)))
