import contextlib
import os
import subprocess

import click
from ruamel.yaml import YAML


def dry_echo(dry, message, *args, **kwargs):
    """
    Print a command to the console (like :func:`click.echo`), but if ``dry`` is True,
    then prefix the message with a warning message stating that the action was
    skipped. All unknown args and kwargs are passed to :func:`click.echo`

    Example usage:

        dry_echo(dry, "Firing ze missiles!", fg='red')
        if not dry:
            fire_ze_missiles()

    Arguments:
        dry (bool): Whether to prefix the dry-run notification
        message: The message to print
    """
    click.echo("{dry}{message}".format(
        dry=click.style("DRY RUN - SKIPPED: ", fg='yellow', bold=True) if dry else "",
        message=click.style(message, *args, **kwargs)
    ))


def dry(f, help='Disable or enable actions taken by the script'):
    """
    A click decorator that adds a ``--dry/--doit`` flag. It is passed to the
    command as ``dry``, and defaults to True.
    """
    return click.option(
        '--dry/--doit',
        is_flag=True,
        default=True,
        help=help,
    )(f)


class YamlLoader:
    def __init__(self, file_path):
        self.file_path = file_path
        self.yml_instance = YAML()
        self.yml_instance.indent(mapping=2, sequence=4, offset=2)
        self._load_file()

    def _load_file(self):
        with open(self.file_path) as file_stream:
            self.elements = self.yml_instance.load(file_stream)

    def update_yml_file(self):
        with open(self.file_path, 'w') as file_stream:
            self.yml_instance.dump(self.elements, file_stream)


def get_cmd_output(cmd):
    """Run a command in shell, and return the Unicode output."""
    try:
        data = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as ex:
        data = ex.output
    try:
        data = data.decode("utf-8")
    except UnicodeDecodeError:
        data = data.decode("latin1")
    return data


@contextlib.contextmanager
def change_dir(new_dir):
    """Change directory, and then change back.

    Use as a context manager, it will give you the new directory, and later
    restore the old one.

    """
    old_dir = os.getcwd()
    os.chdir(new_dir)
    try:
        yield os.getcwd()
    finally:
        os.chdir(old_dir)
