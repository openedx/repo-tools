"""Models of interest to pull request programs."""

import os

import yaml

from helpers import only_once, requests


@only_once
def get_people():
    """Get a dictionary of people.

    Keys are GitHub logins, look at people.yaml to see what information is
    provided.

    """
    # Define REPO_TOOLS_LATEST_PEOPLE=1 in the environment to force code to
    # get people.yaml from GitHub instead of the local copy.
    if int(os.environ.get('REPO_TOOLS_LATEST_PEOPLE', '0')):
        # Read people.yaml from GitHub.
        people_resp = requests.get("https://raw.githubusercontent.com/edx/repo-tools/master/people.yaml")
        if not people_resp.ok:
            people_resp.raise_for_status()
        return yaml.safe_load(people_resp.text)
    else:
        with open("people.yaml") as fpeople:
            return yaml.safe_load(fpeople)


class PullRequestBase(object):

    def short_label(self, lname):
        if lname == "open-source-contribution":
            return "osc"
        if lname.startswith("waiting on "):
            return lname[len("waiting on "):]
        return lname

    @property
    def intext(self):
        internal_orgs = {"edX", "Arbisoft", "BNOTIONS", "OpenCraft", "ExtensionEngine"}
        return "internal" if self.org in internal_orgs else "external"

    @property
    def org(self):
        people = get_people()
        user_info = people.get(self.user_login)
        if not user_info:
            user_info = {"institution": "unsigned"}
        return user_info.get("institution", "other")

    @property
    def combinedstate(self):
        if self.state == 'open':
            return 'open'
        elif self.merged_at:
            return 'merged'
        else:
            return 'closed'

    @property
    def combinedstatecolor(self):
        if self.state == 'open':
            return 'green'
        elif self.merged_at:
            return 'blue'
        else:
            return 'red'
