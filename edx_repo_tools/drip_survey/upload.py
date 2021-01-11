"""
Tools for managing drip-style surveys.

Currently, this only supports translating people.yaml into a Qualtrics CSV.
"""
from backports import csv
from datetime import date
import hashlib
import io
import sys

import click
from edx_repo_tools.data import pass_repo_tools_data

NAME = 'FirstName'
EMAIL = 'Email'
WEEK = 'Week'
ASSOCIATED_WITH = 'AssociatedWith'
UNSUBSCRIBED = 'Unsubscribed'
RECIPIENT_ID = 'RecipientID'


@click.command()
@pass_repo_tools_data
@click.option('--frequency', help="The number of weeks between surveys for each contributor", type=int, default=12)
@click.option('--update', help="A Qualtrics Contact list export to update", type=click.Path(exists=True, dir_okay=False))
def people_to_qualtrics_csv(hub, repo_tools_data, frequency, update):
    """
    Print out a formatted file as expected by Qualtrics import.
    """

    if update is not None:
        with open(update, newline='', encoding='utf-8') as update_data:
            reader = csv.DictReader(update_data)
            initial = {
                row[EMAIL]: row
                for row in reader
            }
        fields = [field for field in reader.fieldnames if field]
    else:
        initial = {}
        fields = [NAME, EMAIL, WEEK, ASSOCIATED_WITH, UNSUBSCRIBED]

    csv_writer = csv.DictWriter(click.get_text_stream('stdout'), fieldnames=fields, extrasaction='ignore')
    csv_writer.writeheader()
    for username, person in repo_tools_data.people.iteritems():
        if person.email is None:
            continue


        hashdigest = hashlib.md5(person.email.lower()).hexdigest()

        row = initial.get(person.email, {})
        row.update({
            NAME: person.name,
            EMAIL: person.email,
            WEEK: int(hashdigest, 16) % frequency + 1,
            ASSOCIATED_WITH: 'edX' if person.associated_with('edX', 'ArbiSoft') else 'other',
        })

        if not person.email_ok:
            row[UNSUBSCRIBED] = 'true'

        csv_writer.writerow(row)

