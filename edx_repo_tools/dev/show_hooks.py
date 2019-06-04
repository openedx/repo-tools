"""Show the hooks in an organization."""

import os.path
import re

import click
from git.repo.base import Repo

from edx_repo_tools.auth import pass_github
from helpers import paginated_get

@click.command()
@click.argument('org')
@click.argument('pattern', required=False)
@pass_github
def main(hub, org, pattern=None):
    for repo in hub.organization(org).repositories():
        printed_repo = False
        url = "https://api.github.com/repos/{name}/hooks".format(name=repo.full_name)
        for r in paginated_get(url):
            if pattern:
                show_it = False
                for v in r['config'].values():
                    if re.search(pattern, v):
                        show_it = True
            else:
                show_it = True

            if show_it:
                if not printed_repo:
                    print("\n-- {} ---------------------".format(repo.full_name))
                    print("  https://github.com/{}/settings/hooks".format(repo.full_name))
                    printed_repo = True
                print("{r[name]}".format(r=r))
                for k, v in sorted(r['config'].items()):
                    print("  {k}: {v}".format(k=k, v=v))
