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
    old_classifiers_regex = r"(?!\s\s+'Framework :: Django :: 3.2')(\s\s+'Framework\s+::\s+Django\s+::\s+[0-3]+\.[0-2]+',)"
    most_recent_classifier_regex = r"\s\s'Framework :: Django :: 3.2',\n"
    # Keep the new classifiers in descending order i.e Framework :: Django :: 4.1 then Framework :: Django :: 4.0 so they are sorted in the file
    new_trove_classifiers = ["\t\t'Framework :: Django :: 4.0',\n"]

    def __init__(self) -> None:
        self.setup_file_path = 'setup.py'

    def _apply_regex_operations(self) -> None:
        file_data = open(self.setup_file_path).read()
        file_data = self._remove_outdated_classifiers(file_data)
        file_data = self._add_new_classifiers(file_data)
        self._write_data_to_file(file_data)

    def _remove_outdated_classifiers(self, file_data) -> str:
        modified_file_data = re.sub(self.old_classifiers_regex, '', file_data)
        return modified_file_data

    def _add_new_classifiers(self, file_data) -> str:
        
        res = re.search(self.most_recent_classifier_regex, file_data)
        end_index_of_most_recent_classifier = res.end()
        modified_file_data = file_data
        for classifier in self.new_trove_classifiers:
            modified_file_data = modified_file_data[:end_index_of_most_recent_classifier] + \
                classifier + \
                modified_file_data[end_index_of_most_recent_classifier:]
        return modified_file_data

    def _write_data_to_file(self, file_data) -> None:
        with open(self.setup_file_path, 'w') as setup_file:
            setup_file.write(file_data)

    def update_setup_file(self) -> None:
        self._apply_regex_operations()


@click.command()
def main():
    setting_modernizer = SetupModernizer()
    setting_modernizer.update_setup_file()


if __name__ == '__main__':
    main()
