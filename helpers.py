"""Helpers for various things."""

import os
import pprint
import re

import requests as real_requests


class WrappedRequests(object):
    """A helper wrapper around requests.

    Provides uniform authentication and logging.
    """

    def __init__(self):
        self.all_requests = None

    def record_request(self, method, url, args, kwargs):
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
        return real_requests.get(url, *args, **self._kwargs(url, kwargs))

    def post(self, url, *args, **kwargs):
        self.record_request("POST", url, args, kwargs)
        return real_requests.post(url, *args, **self._kwargs(url, kwargs))


# Now we can use requests as usual, or even import it from this module.
requests = WrappedRequests()


def paginated_get(url, debug=False, **kwargs):
    """
    Returns a generator that will retrieve all objects from a paginated API.
    Assumes that the pagination is specified in the "link" header, like
    Github's v3 API.
    """
    while url:
        resp = requests.get(url, **kwargs)
        result = resp.json()
        if not resp.ok:
            raise real_requests.exceptions.RequestException(result["message"])
        if debug:
            pprint.pprint(result, stream=sys.stderr)
        for item in result:
            yield item
        url = None
        if "link" in resp.headers:
            match = re.search(r'<(?P<url>[^>]+)>; rel="next"', resp.headers["link"])
            if match:
                url = match.group('url')
