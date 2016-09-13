"""
Top-level definition of the ``drip`` commandline tool.
"""

import click

from edx_repo_tools.drip_survey import upload


@click.group()
def cli():
    """
    Tools for sending out a drip-fed survey.

    The survey will be sent out every FREQUENCY days to each participant,
    but will be staggered so that surveys are sent out to participants
    throughout the survey period.
    """
    pass


cli.add_command(upload.people_to_qualtrics_csv, name='qualtrics-csv')
