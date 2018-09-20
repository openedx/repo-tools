"""Clone an entire GitHub organization."""

import os.path

import click
from git.repo.base import Repo

from edx_repo_tools.auth import pass_github


@click.command()
@click.option(
    '--forks/--no-forks', 'forks', is_flag=True, default=False,
    help="Should forks be included?"
)
@click.argument(
    'org'
)
@pass_github
def main(hub, forks, org):
    for repo in hub.organization(org).iter_repos():
        if repo.fork and not forks:
            continue
        dir_name = repo.name
        if os.path.exists(dir_name):
            continue

        print(repo.full_name)
        Repo.clone_from(repo.ssh_url, dir_name)
