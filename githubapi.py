import operator
import pprint

import dateutil.parser
from urlobject import URLObject
import yaml

from helpers import paginated_get, requests
from models import PullRequestBase


class PullRequest(PullRequestBase):
    def __init__(self, issue_data):
        self._issue = issue_data
        if 0:
            print("---< Issue >---------------------------------")
            pprint.pprint(issue_data)
        self._pull = None
        self.labels = [self.short_label(l['name']) for l in self.labels]

    @classmethod
    def from_json(cls, issues_data):
        for issue_data in issues_data:
            issue = cls(issue_data)
            pr_url = issue._issue.get('pull_request', {}).get('url')
            if not pr_url:
                continue

            yield issue

    ISSUE_FIELDS = {
        'labels', 'number', 'pull_request_url', 'state', 'user_login',
    }
    PULL_FIELDS = {
        'additions', 'base_ref', 'created_at', 'deletions', 'merged_at',
    }
    MAPPED_FIELDS = {
        'base_ref': 'base.ref',
        'pull_request_url': 'pull_request.url',
        'user_login': 'user.login',
    }

    def __getattr__(self, name):
        obj = None
        if name in self.ISSUE_FIELDS:
            obj = self._issue
        elif name in self.PULL_FIELDS:
            obj = self._pull

        if obj is not None:
            name = self.MAPPED_FIELDS.get(name, name)
            val = self.deep_getitem(obj, name)
            if name.endswith('_at') and val is not None:
                val = dateutil.parser.parse(val)
            return val

        raise AttributeError("Nope: don't have {!r} attribute on PullRequest".format(name))

    def deep_getitem(self, val, key):
        for k in key.split("."):
            if val is None:
                break
            val = val[k]
        return val

    def load_pull_details(self, pulls=None):
        """Get pull request details also.

        `pulls` is a dictionary of pull requests, to perhaps avoid making
        another request.

        """
        pull_request = None
        if pulls:
            self._pull = pulls.get(self.number)
        if not self._pull:
            self._pull = requests.get(self.pull_request_url).json()

        if 0:
            print("---< Pull Request >--------------------------")
            pprint.pprint(self._pull)



def get_pulls(owner_repo, labels=None, state="open", since=None, org=False, pull_details=None):
    """
    Get a bunch of pull requests (actually issues).

    `pull_details` indicates how much information you want from the associated
    pull request document.  None means just issue information is enough. "list"
    means the information available when listing pull requests is enough. "all"
    means you need all the details.  See the GitHub API docs for the difference:
    https://developer.github.com/v3/pulls/

    """
    url = URLObject("https://api.github.com/repos/{}/issues".format(owner_repo))
    if labels:
        url = url.set_query_param('labels', ",".join(labels))
    if since:
        url = url.set_query_param('since', since.isoformat())
    if state:
        url = url.set_query_param('state', state)
    url = url.set_query_param('sort', 'updated')

    issues = PullRequest.from_json(paginated_get(url))
    if org:
        issues = sorted(issues, key=operator.attrgetter("org"))

    pulls = None
    if pull_details == "list":
        issues = list(issues)
        if issues:
            # Request a bunch of pull details up front, for joining to.  We can't
            # ask for exactly the ones we need, so make a guess.
            limit = int(len(issues) * 1.5)
            pull_url = URLObject("https://api.github.com/repos/{}/pulls".format(owner_repo))
            if state:
                pull_url = pull_url.set_query_param('state', state)
            pulls = { pr['number']: pr for pr in paginated_get(pull_url, limit=limit) }

    for issue in issues:
        if pull_details:
            issue.load_pull_details(pulls=pulls)
        issue.id = "{}.{}".format(owner_repo, issue.number)
        yield issue
