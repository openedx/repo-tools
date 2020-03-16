"""Clone an entire GitHub organization into current directory."""

import os.path

import click
from git.repo.base import Repo

from edx_repo_tools.auth import pass_github


@click.command()
@click.option(
    '--forks/--no-forks', is_flag=True, default=False,
    help="Should forks be included?"
)
@click.option(
    '--depth', type=int, default=0,
    help="Depth argument for git clone",
)
@click.argument(
    'org'
)
@pass_github
def main(hub, forks, depth, org):
    for repo in hub.organization(org).repositories():
        if repo.fork and not forks:
            continue
        dir_name = repo.name
        dir_name = dir_name.lstrip("-")     # avoid dirname/option confusion
        if os.path.exists(dir_name):
            continue

        print(repo.full_name)
        clone_args = {}
        if depth:
            clone_args['depth'] = depth
        Repo.clone_from(repo.ssh_url, dir_name, **clone_args)
