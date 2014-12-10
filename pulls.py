import operator
import pprint

from helpers import paginated_get, requests
import jreport

from urlobject import URLObject
import yaml


class JPullRequest(jreport.JObj):
    def __init__(self, issue_data, org_fn=None):
        super(JPullRequest, self).__init__(issue_data)
        self['labels'] = [self.short_label(l['name']) for l in self['labels']]
        if org_fn:
            self['org'] = org_fn(self)

            # A pull request is external if marked as such, or if the author's
            # organization is not edX.
            internal_orgs = {"edX", "Arbisoft", "BNOTIONS", "OpenCraft", "ExtensionEngine"}
            if "osc" in self['labels']:
                self['intext'] = "external"
            elif self['org'] in internal_orgs:
                self['intext'] = "internal"
            else:
                self['intext'] = "external"

    def load_pull_details(self, pulls=None):
        """Get pull request details also.

        `pulls` is a dictionary of pull requests, to perhaps avoid making
        another request.

        """
        pull_request = None
        if pulls:
            pull_request = pulls.get(self['number'])
        if not pull_request:
            pull_request = requests.get(self['pull_request.url']).json()
        self['pull'] = pull_request

        if self['state'] == 'open':
            self['combinedstate'] = 'open'
            self['combinedstatecolor'] = 'green'
        elif self['pull.merged_at']:
            self['combinedstate'] = 'merged'
            self['combinedstatecolor'] = 'blue'
        else:
            self['combinedstate'] = 'closed'
            self['combinedstatecolor'] = 'red'

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

            yield issue


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
            user_info = people.get(issue["user.login"])
            if not user_info:
                user_info = {"institution": "unsigned"}
            return user_info.get("institution", def_org)

    issues = JPullRequest.from_json(paginated_get(url), org_fn)
    if org:
        issues = sorted(issues, key=operator.itemgetter("org"))

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
        issue['id'] = "{}.{}".format(owner_repo, issue['number'])
        yield issue
