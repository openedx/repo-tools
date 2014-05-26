import operator

from helpers import paginated_get
import jreport

import requests
from urlobject import URLObject
import yaml


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


def get_pulls(owner_repo, labels=None, state="open", since=None, org=False):
    url = URLObject("https://api.github.com/repos/{}/issues".format(owner_repo))
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
            with open("people.yaml") as fpeople:
                people = yaml.load(fpeople)
            def_org = "other"
        except IOError:
            people = {}
            def_org = "---"

        def org_fn(issue):
            return people.get(issue["user.login"], {}).get("institution", def_org)

    issues = JPullRequest.from_json(paginated_get(url), org_fn)
    if org:
        issues = sorted(issues, key=operator.itemgetter("org"))

    return issues
