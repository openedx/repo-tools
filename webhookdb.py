"""Access WebhookDB."""

from __future__ import print_function

from sqlalchemy import create_engine, MetaData, Table
from sqlalchemy.orm import mapper, sessionmaker

from models import PullRequestBase


class PullRequest(PullRequestBase):
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
        try:
            with open("db.url") as f:
                db = f.read().strip()
        except Exception:
            raise ValueError("It looks like you don't have a `db.url` file. Please contact someone on the Open Source team to help you out.")
            
        engine = create_engine(db)
        meta = MetaData(engine)

        mapper(PullRequest, Table('github_pull_request', meta, autoload=True))
        mapper(PullRequestFile, Table('github_pull_request_file', meta, autoload=True))
        mapper(Repository, Table('github_repository', meta, autoload=True))
        mapper(User, Table('github_user', meta, autoload=True))

        if 0:
            print("PullRequest")
            print(dir(PullRequest))
            print()
            print("PullRequestFile")
            print(dir(PullRequestFile))
            print()
            print("Repository")
            print(dir(Repository))
            print()
            print("User")
            print(dir(User))

        Session = sessionmaker(bind=engine)
        session = Session()

    return session


def get_pulls(owner_repo, labels=None, state="open", since=None, org=False, pull_details=None):
    session = init_sqlalchemy()

    user_login, repo_name = owner_repo.split("/")
    user = session.query(User).filter(User.login==user_login)[0]
    try:
        repo = session.query(Repository).filter(Repository.name==repo_name).filter(Repository.owner_id==user.id)[0]
    except IndexError:
        return ()   # no repo means no pulls
    try:
        q = session.query(PullRequest).filter(PullRequest.base_repo_id==repo.id)
        if state != "all":
            q = q.filter(PullRequest.state==state)
        if since is not None:
            q = q.filter(PullRequest.updated_at>=since)
        pulls = q.all()
    except IndexError:
        pulls = []

    if 0:
        print("{} pulls from {} with state {}:".format(len(pulls), owner_repo, state))
        #for pull in pulls:
        #    print(" {p.number:-4d}: {p.title}".format(p=pull))

    return pulls
