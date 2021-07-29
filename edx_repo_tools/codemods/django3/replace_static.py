import click
import subprocess


@click.command()
@click.option('--path', help='use syntax: --path {path_to_input_file/directory}')
def main(path):
    """
    Function to handle input path for refactoring.
    HOW_TO_USE: when running as a repo tool, use following syntax to run the command:
        replace_staticfiles --path {path_to_input_file/directory}
    """
    subprocess.run(['./edx_repo_tools/codemods/django3/script_to_replace_static.sh', path])


if __name__ == '__main__':
    main()

