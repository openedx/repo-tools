"""Clone an entire GitHub organization into current directory."""

import os.path
import shutil

import click
from git.repo.base import Repo

from edx_repo_tools.auth import pass_github


@click.command()
@click.option(
    '--archived/--no-archived', is_flag=True, default=False,
    help="Should archived repos be included?"
)
@click.option(
    '--archived-only', is_flag=True, default=False,
    help="Should only archived repos be cloned?"
)
@click.option(
    '--forks/--no-forks', is_flag=True, default=False,
    help="Should forks be included?"
)
@click.option(
    '--forks-only', is_flag=True, default=False,
    help="Should only forks be cloned?"
)
@click.option(
    '--depth', type=int, default=0,
    help="Depth argument for git clone",
)
@click.option(
    '--prune', is_flag=True, default=False,
    help="Remove repos that we wouldn't have cloned",
)
@click.argument(
    'org'
)
@pass_github
def main(hub, archived, archived_only, forks, forks_only, depth, prune, org):
    """
    Clone an entire GitHub organization into the current directory.
    Each repo becomes a subdirectory.
    """
    if archived_only:
        archived = True
    if forks_only:
        forks = True
    dir_names = set()
    for repo in hub.organization(org).repositories():
        if repo.fork and not forks:
            continue
        if not repo.fork and forks_only:
            continue
        if repo.archived and not archived:
            continue
        if not repo.archived and archived_only:
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
