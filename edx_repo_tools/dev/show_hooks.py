"""Show the hooks in an organization."""

import os.path

import click
from git.repo.base import Repo

from edx_repo_tools.auth import pass_github
from helpers import paginated_get

@click.command()
@click.argument('org')
@pass_github
def main(hub, org):
    for repo in hub.organization(org).iter_repos():
        print("\n-- {} ---------------------".format(repo.full_name))
        url = "https://api.github.com/repos/{name}/hooks".format(name=repo.full_name)
        for r in paginated_get(url):
            print("{r[name]}".format(r=r))
            for k, v in sorted(r['config'].items()):
                print("  {k}: {v}".format(k=k, v=v))
