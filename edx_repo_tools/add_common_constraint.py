import re
from os import path
import urllib.request

import click

FILES = [
    'requirements/constraint.txt',
    'requirements/constraints.txt',
    'requirements/pins.txt',
]


class CommonConstraint:
    """
        CommonConstraint class is responsible for adding common constraint pin in
        the constraints file of the repository
    """

    def __init__(self):
        self.comment = "# Common constraints for edx repos\n"
        self.constraint = "-c https://raw.githubusercontent.com/edx/edx-lint/master/edx_lint/files/common_constraints" \
                          ".txt\n "
        self.file = self._get_file_name()
        self.lines = []

    def _get_file_name(self):
        for file in FILES:
            if path.exists(file):
                return file

    def _read_lines(self):
        with open(self.file, 'r') as file:
            self.lines = file.readlines()

    def _get_constraint_index(self):
        for i in range(len(self.lines)):
            if not self.lines[i].lstrip().startswith('#'):
                if self.lines[i] == '\n':
                    return i + 1
        return 0

    def _get_constraints(self):
        target_url = "https://raw.githubusercontent.com/edx/edx-lint/master/edx_lint/files/common_constraints.txt"

        packages = []
        for raw_line in urllib.request.urlopen(target_url):
            line = raw_line.decode('utf-8')
            package = re.search('^[A-Za-z0-9-_]+(<|==|>)', line)
            if package:
                packages.append(re.sub("(<=|==|>=|>|<)([0-9]*.*)\n", "", package.string.lower()))
        return packages

    def _remove_common_constraints(self):
        constraints = self._get_constraints()
        for index, line in enumerate(self.lines):
            package = re.search('^[A-Za-z0-9-_]+(<|==|>)', line)
            if package:
                if re.sub("(<=|==|>=|>|<)([0-9]*.*)\n", "", package.string.lower()) in constraints:
                    del self.lines[index]
                    if self.lines[index - 1].lstrip().startswith('#'):
                        del self.lines[index - 1]
                    if self.lines[index - 2] == '\n':
                        del self.lines[index - 1]

    def _insert_constraint(self):
        index = self._get_constraint_index()

        self.lines.insert(index, self.comment)
        self.lines.insert(index + 1, self.constraint)
        self.lines.insert(index + 2, "\n")

        return self.lines

    def _write_file(self):
        with open(self.file, 'w') as file:
            file.writelines(self.lines)

    def update_file(self):
        if self.file is None:
            raise click.ClickException('No constraint file exists!')

        self._read_lines()
        self._insert_constraint()
        self._remove_common_constraints()
        self._write_file()

        click.echo('Added common constraint successfully!')


@click.command()
def main():
    constraint = CommonConstraint()
    constraint.update_file()


if __name__ == "__main__":
    main()
