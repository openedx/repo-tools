"""
Audit github users in an org.  Comparing the list of users to those in a CSV.

See the README for more info.
"""

import base64
import csv
import io
from fnmatch import fnmatchcase
from itertools import chain
import click
from ghapi.all import GhApi, sync_paged
import requests

# Users missing from the CSV are only worth investigating if they are on a team
# that doesn't match one of these patterns. Add team names, or shell-style
# wildcards like "wg-*", here to stop them from being flagged.
IGNORED_TEAMS = (
    "openedx-triage",
    "interest-performance",
    "edunext-website",
    "openedx-product-managers",
    "bot-*",
    "wg-*",
)


def _is_ignored_team(name):
    """
    Return True if the team name matches one of IGNORED_TEAMS.
    """
    return any(fnmatchcase(name, pattern) for pattern in IGNORED_TEAMS)


@click.command()
@click.option(
    "--github-token",
    "_github_token",
    envvar="GITHUB_TOKEN",
    required=True,
    help="A github personal access token.",
)
@click.option(
    "--org",
    "org",
    default="openedx",
    help="The github org that you wish check.",
)
@click.option(
    "--csv-repo",
    "csv_repo",
    default="openedx-webhooks-data",
    help="The github repo that contains the CSV we should compare against.",
)
@click.option(
    "--csv-path",
    "csv_path",
    default="salesforce-export.csv",
    help="The path in the repo to the csv file. The file should contain a 'GitHub Username' column.",
)
def main(org, _github_token, csv_repo, csv_path):
    """
    Entry point for command-line invocation.
    """
    api = GhApi(token=_github_token, sync=True)

    # Get all github users in the org.
    current_org_users = [
        member.login
        for member in chain.from_iterable(
            sync_paged(api.orgs.list_members, org, per_page=100)
        )
    ]

    # Get all github usernames from openedx-webhooks-data/salesforce-export.csv
    csv_file = io.StringIO(
        base64.decodebytes(
            api.repos.get_content(org, csv_repo, csv_path).content.encode()
        ).decode("utf-8")
    )
    reader = csv.DictReader(csv_file)
    csv_github_users = [row["GitHub Username"] for row in reader]

    # Find all the people that are in the org but not in sales force.
    extra_org_users = set(current_org_users) - set(csv_github_users)

    # Find users who are on at least one team that isn't in IGNORED_TEAMS.
    # Using the GraphQL API because there is no good GitHub rest API for this.
    extra_org_users_not_triage = []
    for user in extra_org_users:
        json = { 'query' : f"""{{
                    organization(login:"openedx"){{
                        teams(userLogins:"{user}",first:10) {{
                            nodes {{name}}
                            totalCount
                        }}
                    }}
                }}"""}
        headers = {'Authorization': f'token {_github_token}'}

        r = requests.post(url='https://api.github.com/graphql', json=json, headers=headers)

        result = r.json()
        team_data = result['data']['organization']['teams']
        team_list = [team['name'] for team in team_data['nodes']]
        # Teams past the first page aren't visible, so assume they're relevant.
        has_unseen_teams = team_data['totalCount'] > len(team_list)
        if has_unseen_teams or any(not _is_ignored_team(name) for name in team_list):
            extra_org_users_not_triage.append(f"{user} - teams: {team_list}")

    # List the users we need to investigate
    print("\n" + "Users to investigate (first 10 teams listed):")
    print("\n" + "\n".join(sorted(extra_org_users_not_triage)))


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
