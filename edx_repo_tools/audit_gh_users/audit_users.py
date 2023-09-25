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

    # List the users we need to investigate
    print("\n".join(sorted(extra_org_users)))


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
