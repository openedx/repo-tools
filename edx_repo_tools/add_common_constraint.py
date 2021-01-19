from os import path

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
        self._read_lines()
        self._insert_constraint()
        self._write_file()


@click.command()
def main():
    constraint = CommonConstraint()
    constraint.update_file()


if __name__ == "__main__":
    main()
