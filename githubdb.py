"""Access GitHubDB."""

from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import mapper, sessionmaker

import datetime
import yaml

from helpers import make_timezone_aware

people = None

def init_people():
    global people
    if people is None:
        with open("people.yaml") as fpeople:
            people = yaml.load(fpeople)
    return people

def date_silliness(d):
    if d is None:
        return None
    return make_timezone_aware(d).isoformat()

class PullRequest(object):
    def __getitem__(self, key):
        if key == "intext":
            internal_orgs = {"edX", "Arbisoft", "BNOTIONS", "OpenCraft", "ExtensionEngine"}
            return "internal" if self['org'] in internal_orgs else "external"
        elif key == "user.login":
            return self.user_login
        elif key == "org":
            people = init_people()
            user_info = people.get(self.user_login)
            if not user_info:
                user_info = {"institution": "unsigned"}
            return user_info.get("institution", "other")
        elif key == 'created_at':
            return date_silliness(self.created_at)
        elif key == 'pull.merged_at':
            return date_silliness(self.merged_at)
        elif key == "combinedstate":
            if self['state'] == 'open':
                return 'open'
            elif self['pull.merged_at']:
                return 'merged'
            else:
                return 'closed'
        elif key in {'number', 'title', 'state', 'pull.additions', 'pull.deletions', 'base_ref'}:
            return getattr(self, key.replace('pull.', ''))
        else:
            try:
                print "getitem, returning attr:", key
                val = getattr(self, key)
                print "--> %r" % val
                return val
            except AttributeError:
                raise Exception("No key! {}".format(key))

    def get_files(self):
        files = session.query(PullRequestFile).filter(PullRequestFile.pull_request_id==self.id).all()
        return files

class Repository(object):
    pass

class User(object):
    pass

class PullRequestFile(object):
    pass


engine = session = None

def init_sqlalchemy():
    global engine, session

    if engine is None:
        with open("db.url") as f:
            db = f.read().strip()
        engine = create_engine(db)
        meta = MetaData(engine)

        mapper(PullRequest, Table('githubdb_pull_request', meta, autoload=True))
        mapper(PullRequestFile, Table('githubdb_pull_request_file', meta, autoload=True))
        mapper(Repository, Table('githubdb_repository', meta, autoload=True))
        mapper(User, Table('githubdb_user', meta, autoload=True))

        if 0:
            print "PullRequest"
            print dir(PullRequest)
            print
            print "PullRequestFile"
            print dir(PullRequestFile)
            print
            print "Repository"
            print dir(Repository)
            print
            print "User"
            print dir(User)

        Session = sessionmaker(bind=engine)
        session = Session()

    return session


def get_pulls(owner_repo, labels=None, state="open", since=None, org=False, pull_details=None):
    assert state == "all", "Haven't implemented anything but state='all'"

    session = init_sqlalchemy()
    people = init_people()

    user_login, repo_name = owner_repo.split("/")
    user = session.query(User).filter(User.login==user_login)[0]
    try:
        repo = session.query(Repository).filter(Repository.name==repo_name).filter(Repository.owner_id==user.id)[0]
    except IndexError:
        return ()   # no repo means no pulls
    try:
        pulls = session.query(PullRequest).filter(PullRequest.base_repo_id==repo.id).all()
    except IndexError:
        pulls = []

    return pulls
