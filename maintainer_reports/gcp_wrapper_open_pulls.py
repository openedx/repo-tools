import click
from graphql_requests import *

if __name__=='__main__':
    #
    # Wrapping this in a try block to prevent Click from exiting directly.
    # GCP Cloud Functions doesn't want programs to do so, but return so their
    # wrapper can handle cleanly exiting the environment.
    #
    try:
        # pylint: disable=no-value-for-parameter
        cli(["handle-open-pulls"])
    except SystemExit as e:
        if e.code != 0:
            raise
