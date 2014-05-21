import sys
import re
import requests
import pprint


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
            raise requests.exceptions.RequestException(result["message"])
        if debug:
            pprint.pprint(result, stream=sys.stderr)
        for item in result:
            yield item
        url = None
        if "link" in resp.headers:
            match = re.search(r'<(?P<url>[^>]+)>; rel="next"', resp.headers["link"])
            if match:
                url = match.group('url')
