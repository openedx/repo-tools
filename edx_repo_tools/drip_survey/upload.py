"""
Tools for managing drip-style surveys.

Currently, this only supports translating people.yaml into a Qualtrics CSV.
"""
import csv
from datetime import date
import hashlib
import sys

import click
from edx_repo_tools.data import pass_repo_tools_data

NAME = 'FirstName'
EMAIL = 'PrimaryEmail'
WEEK = 'Week'
ASSOCIATED_WITH = 'AssociatedWith'
UNSUBSCRIBED = 'Unsubscribed'

def associated_with(person):
    if person.get('agreement') != 'institution':
        return 'other'

    if 'expires_on' in person and person['expires_on'] < date.today():
        return 'other'

    if person.get('institution', '').lower() in ('edx', 'arbisoft'):
        return 'edX'

    return 'other'

@click.command()
@pass_repo_tools_data
@click.option('--frequency', help="The number of weeks between surveys for each contributor", type=int, default=12)
def people_to_qualtrics_csv(hub, repo_tools_data, frequency):
    """
    Print out a formatted file as expected by Qualtrics import.
    """

    csv_writer = csv.DictWriter(sys.stdout, [NAME, EMAIL, WEEK, ASSOCIATED_WITH, UNSUBSCRIBED])
    csv_writer.writeheader()
    for username, person in repo_tools_data.people.iteritems():
        if person.get('email') is None:
            continue

        email = person['email']

        hashdigest = hashlib.md5(email.lower()).hexdigest()

        row = {
            NAME: person['name'].encode('utf-8'),
            EMAIL: email.encode('utf-8'),
            WEEK: int(hashdigest, 16) % frequency,
            ASSOCIATED_WITH: associated_with(person),
        }

        if not person.get('email_ok', True):
            row[UNSUBSCRIBED] = 'true'

        csv_writer.writerow(row)

