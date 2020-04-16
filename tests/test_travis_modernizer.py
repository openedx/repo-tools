import os
import re
import shutil
import uuid
from django3_codemods.config_tools.travis_modernizer import TravisModernizer
from unittest import TestCase


class TravisModernizerTest(TestCase):

    def setUp(self):
        self.test_file1 = self._setup_local_copy("test_travis.yml")
        self.test_file2 = self._setup_local_copy("test_travis_2.yml")
        self.DJANGO_PATTERN = "django[0-2][0-1]"  # creates regex to match django111, django20 && django21

    @staticmethod
    def _setup_local_copy(file_name):
        current_directory = os.path.dirname(__file__)
        temp_file = os.path.join(current_directory, str(uuid.uuid4()) + ".yml")
        local_file = os.path.join(current_directory, file_name)
        shutil.copy2(local_file, temp_file)
        return temp_file

    @staticmethod
    def _get_parser(file_path):
        parser = TravisModernizer(file_path=file_path)
        return parser

    def _assert_django_versions_removed(self, test_file):
        parser = self._get_parser(test_file)
        parsed_data = parser.remove_django_envs()
        if 'matrix' in parsed_data.keys():
            env_list = parsed_data['matrix']['include']
            for env in env_list:
                self.assertNotRegex(self.DJANGO_PATTERN, env['env'])
        if 'env' in parsed_data.keys():
            env_list = parsed_data['env']
            for env in env_list:
                self.assertNotRegex(self.DJANGO_PATTERN, env)

    def _assert_python_versions_updated(self, test_file):
        parser = self._get_parser(test_file)
        parsed_data = parser.update_python_version()
        if 'python' in parsed_data.keys():
            self.assertIn('3.8', parsed_data['python'])
            self.assertNotIn('3.6', parsed_data['python'])
        if 'matrix' in parsed_data.keys():
            env_list = parsed_data['matrix']['include']
            python_versions = set([env['python'] for env in env_list])
            self.assertIn('3.8', python_versions)
            self.assertNotIn('3.6', python_versions)

    def test_django_versions_removed(self):
        self._assert_django_versions_removed(self.test_file1)
        self._assert_django_versions_removed(self.test_file2)

    def test_python_version_added(self):
        self._assert_python_versions_updated(self.test_file1)
        self._assert_python_versions_updated(self.test_file2)

    def tearDown(self):
        os.remove(self.test_file1)
        os.remove(self.test_file2)

