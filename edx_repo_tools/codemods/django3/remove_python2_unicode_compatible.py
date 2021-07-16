"""
A script to remove the python2_unicode_compatible imports and headers
"""
import sys
import click
from bowler import Query


def remove_node(node, _, __):
    """
    Remove the node containing the expression python_2_unicode_compatible
    """
    node.remove()


def run_removal_query(path):
    """
    Run the bowler query on the input files for refactoring.
    """
    (
        Query(path)
        .select("decorator<'@' name='python_2_unicode_compatible' any>")
        .modify(remove_node)
        .select("import_from<'from' module_name=any 'import' 'python_2_unicode_compatible'>")
        .modify(remove_node)
        .write()
    )


@click.command()
@click.option('--path', help='use syntax: --path {path_to_input_file/directory}')
def main(path):
    """
    Function to handle input path for refactoring.
    HOW_TO_USE: when running as a repo tool, use following syntax to run the command:
        remove_python2_unicode_compatible --path {path_to_input_file/directory}
    """
    run_removal_query(path)


if __name__ == '__main__':
    main()
