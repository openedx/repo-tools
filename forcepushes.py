from __future__ import print_function

import pprint

import uritemplate

from helpers import paginated_get


EVENTS_URL = "https://api.github.com/repos/{owner}/{repo}/events"

url = uritemplate.expand(EVENTS_URL, owner='edx', repo='edx-platform')
for event in paginated_get(url):
    if event['type'] != 'PushEvent':
        continue
    forced = event['payload'].get('forced', False)
    print("{0[created_at]}: {0[type]}, {0[actor][login]} {1}".format(event, forced))
