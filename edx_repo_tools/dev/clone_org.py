"""Clone an entire GitHub organization into current directory."""

import os.path
import shutil

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
@click.option(
    '--prune', is_flag=True, default=False,
    help='Remove repos that are gone from GitHub'
)
@click.argument(
    'org'
)
@pass_github
def main(hub, forks, depth, prune, org):
    """
    Clone an entire GitHub organization into the current directory.
    Each repo becomes a subdirectory.
    """
    dir_names = set()
    for repo in hub.organization(org).repositories():
        if repo.fork and not forks:
            continue
        dir_name = repo.name
        dir_name = dir_name.lstrip("-")     # avoid dirname/option confusion
        dir_names.add(dir_name)
        if os.path.exists(dir_name):
            continue

        print("Cloning {}".format(repo.full_name))
        clone_args = {}
        if depth:
            clone_args['depth'] = depth
        Repo.clone_from(repo.ssh_url, dir_name, **clone_args)

    if prune:
        for dir_name in os.listdir("."):
            if os.path.isdir(dir_name):
                if dir_name not in dir_names:
                    print("Pruning {}".format(dir_name))
                    shutil.rmtree(dir_name)
