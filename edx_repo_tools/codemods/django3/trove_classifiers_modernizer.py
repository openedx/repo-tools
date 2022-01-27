"""
Codemod to modernizer setup file.
"""
import json
import os
import re
from copy import deepcopy

import click


class SetupModernizer:
    """
    Django32 modernizer for updating setup files.
    """
    # Keep these spaces in the regex intact
    classifiers_regex = r"(?!\s\s+'Framework :: Django :: 3.2')(\s\s+'Framework\s+::\s+Django\s+::\s+[0-3]+\.[0-2]+',)"

    def __init__(self) -> None:
        self.setup_file_path = 'setup.py'
        
    def _apply_regex_operations(self):
        file_data = open(self.setup_file_path).read()
        file_data = re.sub(self.classifiers_regex, '', file_data)
        return deepcopy(file_data)

    def update_setup_file(self):
        file_data = self._apply_regex_operations()
        with open(self.setup_file_path, 'w') as setup_file:
            setup_file.write(file_data)


@click.command()
def main():
    setting_modernizer = SetupModernizer()
    setting_modernizer.update_setup_file()


if __name__ == '__main__':
    main()
