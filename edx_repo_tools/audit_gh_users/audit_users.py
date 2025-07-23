"""
Audit github users in an org.  Comparing the list of users to those in a CSV.

See the README for more info.
"""

import base64
import csv
import io
from itertools import chain
import click
from ghapi.all import GhApi, paged
import requests


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
    api = GhApi()

    # Get all github users in the org.
    current_org_users = [
        member.login
        for member in chain.from_iterable(
            paged(api.orgs.list_members, org, per_page=100)
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

    # Find users who are in multiple teams or a single non-triage team
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
        if team_data['totalCount'] > 1:
            team_list = []
            for team in team_data['nodes']:
                team_list.append(team['name'])
            extra_org_users_not_triage.append(f"{user} - teams: {team_list}")
        elif team_data['totalCount'] == 1 and team_data['nodes'][0]['name'] != 'openedx-triage':
            extra_org_users_not_triage.append(f"{user} - teams: ['{team_data['nodes'][0]['name']}']")

    # List the users we need to investigate
    print("\n" + "\n".join(sorted(extra_org_users_not_triage)))


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
