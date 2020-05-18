"""Get the urls to every repository in a GitHub organization."""

import os.path

import click
from git.repo.base import Repo

from edx_repo_tools.auth import pass_github


@click.command()
@click.option(
    '--forks/--no-forks', is_flag=True, default=False,
    help="Should forks be included?"
)
@click.argument(
    'org'
)
@click.option(
    '--url_type', default="ssh",
    help="options: ssh or https"
)
@click.option(
    '--output_file', default="repositories.txt",
    help="where should script output urls"
)
@click.option(
    '--add_archived', is_flag=True, default=False,
    help="Do you want urls for archived repos?")
@pass_github
def main(hub, forks, org, url_type, output_file, add_archived):
    """
    Used to get the urls for all the repositories in a github organization
    """
    repositories = []
    for repo in hub.organization(org).repositories():
        if repo.fork and not forks:
            continue
        if repo.archived and not add_archived:
            continue
        if url_type == "ssh":
            repositories.append(repo.ssh_url)
        else:
            repositories.append(repo.clone_url)
    with open(output_file, 'w') as filehandle:
        for repo_url in repositories:
            filehandle.write('%s\n' % repo_url)
