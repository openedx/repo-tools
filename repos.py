import yaml

class Repo(object):
    @classmethod
    def from_yaml(cls, filename="repos.yaml"):
        with open(filename) as yaml_file:
            all_repos = yaml.load(yaml_file)

        for name, data in all_repos.iteritems():
            yield cls(name, data)

    def __init__(self, name, data):
        self.name = name
        data = data or {}
        self.track_pulls = data.get("track-pulls", False)
        self.nick = data.get("nick", name)

    def __repr__(self):
        return "<Repo {0.name!r}>".format(self)
