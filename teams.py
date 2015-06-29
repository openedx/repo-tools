#!/usr/bin/env python
"""Play around with teams."""

from __future__ import print_function

import pprint

import click
import uritemplate
import yaml

from helpers import paginated_get


@click.group()
def cli():
    """Work with GitHub teams, etc."""
    pass


TEAMS_URL = "https://api.github.com/orgs/{org}/teams"

@cli.command(name="list")
def list_():
    """Lists the teams.

    Also shows permissions, members, and repos.

    """
    teams = list(paginated_get(uritemplate.expand(TEAMS_URL, org="edX")))
    for team in teams:
        print("{0[name]}:".format(team))
        print("    permission: {0[permission]}".format(team))

        members_url = uritemplate.expand(team['members_url'])
        members = list(paginated_get(members_url))
        print("    members:   # {}".format(len(members)))
        for member in members:
            print("        - {0[login]}".format(member))

        repos_url = uritemplate.expand(team['repositories_url'])
        repos = list(paginated_get(repos_url))
        print("    repos:    # {}".format(len(repos)))
        for repo in repos:
            print("        - {0[full_name]}".format(repo))


if __name__ == '__main__':
    cli()
