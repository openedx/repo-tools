import click
from graphql_requests import *

def main(data, context):
    """
    Wrapper function following recommended pattern for 
    GCP Cloudfunctions.
    """
    # Wrapping this in a try block to prevent Click from exiting directly.
    # GCP Cloud Functions doesn't want programs to do so, but return so their
    # wrapper can handle cleanly exiting the environment.
    #
    try:
        # pylint: disable=no-value-for-parameter
        cli(["handle-open-pulls"])
    except SystemExit as sys_exit:
        if sys_exit.code != 0:
            raise


if __name__=='__main__':
    main('data','context')
