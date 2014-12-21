import yaml

people = None

def init_people():
    global people
    if people is None:
        with open("people.yaml") as fpeople:
            people = yaml.load(fpeople)
    return people

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
        people = init_people()
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
