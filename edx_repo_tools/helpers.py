"""Helpers for various things."""


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


class WrappedRequests:
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
            print(f"{method} {url}")
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
            print(f"GET {url}: {info}")
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
