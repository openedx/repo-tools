"""
Codemod to add new settings in the repo settings file.
"""
import json
import re
import os
import click
from copy import deepcopy


class SettingsModernizer:
    """
    Django32 modernizer for updating settings files.
    """
    DEFAULT_ALGORITHM_KEY = "DEFAULT_HASHING_ALGORITHM"
    NEW_HASHING_ALGORITHM = "sha1"
    DEFAULT_FIELD_KEY = "DEFAULT_AUTO_FIELD"
    NEW_AUTO_FIELD = "django.db.models.AutoField"
    NEW_PROCESSOR = "django.template.context_processors.request"

    def __init__(self, setting_path, is_service):
        self.settings_path = setting_path
        self.is_service = is_service

    def _apply_regex_operations(self, matching_pattern, new_pattern, context_processors=False):
        file_data = open(self.settings_path).read()
        if context_processors:
            if self.NEW_PROCESSOR not in file_data and re.search("context_processors", file_data):
                file_data = re.sub(pattern=matching_pattern, repl=new_pattern, string=file_data)
        else:
            file_data = re.sub(pattern=matching_pattern, repl="", string=file_data)
            file_data = file_data+new_pattern
        return deepcopy(file_data)

    def _update_settings_file(self, matching_pattern, new_pattern, context_processors=False):
        file_data = self._apply_regex_operations(matching_pattern, new_pattern, context_processors)
        with open(self.settings_path, 'w') as setting_file:
            setting_file.write(file_data)

    def update_settings(self):
        if self.is_service:
            self.update_hash_algorithm()
        self.update_auto_field()
        self.update_context_processors()

    def update_hash_algorithm(self):
        """
        Update the HASHING_ALGORITHM in the settings file.
        """
        matching_algorithm = f"{self.DEFAULT_ALGORITHM_KEY}\s=\s'[a-zA-Z0-9]*'\\n"
        new_algorithm = f"{self.DEFAULT_ALGORITHM_KEY} = '{self.NEW_HASHING_ALGORITHM}'\n"
        self._update_settings_file(matching_algorithm, new_algorithm)

    def update_auto_field(self):
        """
        Update the AUTO_FIELD in the settings file.
        """
        matching_field = f"{self.DEFAULT_FIELD_KEY}\s=\s'([a-zA-Z](.[a-zA-Z])?)*'\\n"
        new_field = f"{self.DEFAULT_FIELD_KEY} = '{self.NEW_AUTO_FIELD}'\n"
        self._update_settings_file(matching_field, new_field)

    def update_context_processors(self):
        """
        Update the CONTEXT_PROCESSORS in the settings file.
        """
        matching_pattern = fr"'context_processors': \(([^)]*)\)"
        new_pattern = fr"'context_processors': (\1" + f"\t'{self.NEW_PROCESSOR}',\n\t\t\t\t)"
        self._update_settings_file(matching_pattern, new_pattern, context_processors=True)


@click.command()
@click.option('--setting_path', default='settings/base.py', help="Path to the settings file to update")
@click.option('--is_service', default=False, help="Flag for service/library, pass True for service")
def main(setting_path, is_service):
    setting_modernizer = SettingsModernizer(setting_path, is_service)
    setting_modernizer.update_settings()


if __name__ == '__main__':
    main()
