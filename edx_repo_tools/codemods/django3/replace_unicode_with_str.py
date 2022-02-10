import sys

import click
from bowler import Query


def replace_unicode(path):
    """
    Run the bowler query on the input files for refactoring.
    """
    (
        Query(path)
        .select_function("__unicode__")
        .rename('__str__')
        .idiff()
    ),
    (
        Query(path)
        .select_method("__unicode__")
        .is_call()
        .rename('__str__')
        .idiff()
    )


@click.command()
@click.option('--path', help='use syntax: --path {path_to_input_file/directory}')
def main(path):
    """
    Function to handle input path for refactoring.
    HOW_TO_USE: when running as a repo tool, use following syntax to run the command:
        replace_unicode_with_str --path {path_to_input_file/directory}
    """
    replace_unicode(path)


if __name__ == '__main__':
    main()

