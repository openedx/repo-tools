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

    def _get_file_name(self):
        for file in FILES:
            if path.exists(file):
                return file

    def _read_lines(self):
        with open(self.file, 'r') as file:
            lines = file.readlines()
        return lines

    def _insert_constraint(self, lines):
        for i in range(len(lines)):
            if not lines[i].lstrip().startswith('#'):
                lines.insert(i, "\n")
                lines.insert(i + 1, self.comment)
                lines.insert(i + 2, self.constraint)
                return lines

    def _write_file(self, lines):
        with open(self.file, 'w') as file:
            file.writelines(lines)

    def update_file(self):
        lines = self._read_lines()
        lines = self._insert_constraint(lines)
        self._write_file(lines)


@click.command()
def main():
    constraint = CommonConstraint()
    constraint.update_file()


if __name__ == "__main__":
    main()
