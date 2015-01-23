"""Models of interest to pull request programs."""

from people import People


class PullRequestBase(object):

    def short_label(self, lname):
        if lname == "open-source-contribution":
            return "osc"
        if lname.startswith("waiting on "):
            return lname[len("waiting on "):]
        return lname

    @property
    def intext(self):
        # We don't always have labels.
        if "osc" in getattr(self, 'labels', ()):
            return "external"
        internal_orgs = {"edX", "Arbisoft", "BNOTIONS", "Clarice", "OpenCraft", "ExtensionEngine"}
        if self.org in internal_orgs:
            return "internal"
        else:
            return "external"

    @property
    def org(self):
        people = People.people()
        user_info = people.get(self.user_login, self.created_at)
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
