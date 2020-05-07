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
@click.option(
    '--output_file', default="repositories.txt")
@pass_github
def main(hub, forks, depth, org, output_file):
    repositories = []
    for repo in hub.organization(org).repositories():
        if repo.fork and not forks:
            continue
        repositories.append(repo.ssh_url)
    with open(output_file, 'w') as filehandle:
        for repo_url in repositories:
            filehandle.write('%s\n' % repo_url)
