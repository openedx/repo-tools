"""Tests for TOX modernizer """
import os
import re
from configparser import NoSectionError, ConfigParser
from unittest import TestCase
import shutil
import uuid
from edx_repo_tools.codemods.django3 import ConfigReader


class TestToxModernizer(TestCase):
    def setUp(self):
        self.config_file1 = self._setup_local_copy("sample_tox_config.ini")
        self.config_file2 = self._setup_local_copy("sample_tox_config_2.ini")

    @staticmethod
    def _setup_local_copy(file_name):
        current_directory = os.path.dirname(__file__)
        temp_file = os.path.join(current_directory, str(uuid.uuid4()) + ".ini")
        local_file = os.path.join(current_directory, file_name)
        shutil.copy2(local_file, temp_file)
        return temp_file

    def _get_parser(self, file_path):
        modernizer = ConfigReader(file_path=file_path).get_modernizer()
        modernizer.modernize()
        parser = ConfigParser()
        parser.read(file_path)
        self._assert_no_tabs(file_path)
        return parser

    def _assert_django_dependencies_replaced(self, config_file):
        parser = self._get_parser(config_file)
        dependencies = parser['testenv']['deps']

        self.assertNotIn("django111:", dependencies)
        self.assertNotIn("django20:", dependencies)
        self.assertNotIn("django21:", dependencies)
        self.assertIn("django22:", dependencies)
        self.assertIn("django30:", dependencies)

    def _assert_replaces_python_interpreters(self, config_file):
        parser = self._get_parser(config_file)
        env_list = parser['tox']['envlist']

        self.assertNotRegex("py{27}", env_list)
        self.assertNotIn("py{27,35}", env_list)
        self.assertNotIn("py{27,35,36}", env_list)
        self.assertNotIn("py{27,35,36,37}", env_list)
        self.assertIn("py38", env_list)

    def _assert_replaces_django_runners(self, config_file):
        parser = self._get_parser(config_file)
        env_list = parser['tox']['envlist']

        self.assertNotIn("django{111}", env_list)
        self.assertNotIn("django{111,20}", env_list)
        self.assertNotIn("django{111,20,21}", env_list)
        self.assertIn("django{22,30,31}", env_list)

    def _assert_replaces_django_dependencies(self, config_file):
        self._assert_django_dependencies_replaced(config_file)

    def _assert_adds_django_dependencies(self, config_file):
        parser = ConfigParser()
        parser.read(config_file)

        dependencies = parser['testenv']['deps']
        dependencies = re.sub("[^\n]*django22.*\n", '', dependencies)
        parser['testenv']['deps'] = dependencies

        with open(config_file, 'w') as configfile:
            parser.write(configfile)

        self._assert_django_dependencies_replaced(config_file)

    def _assert_no_tabs(self, config_file):
        with open(config_file) as configfile:
            assert "\t" not in configfile.read()

    def test_raises_error_no_empty_config(self):
        tox_config = {}
        self.assertRaises(NoSectionError, ConfigReader(config_dict=tox_config).get_modernizer)

    def test_raises_error_bad_config(self):
        tox_config = {'section1': {'key1': 'value1', 'key2': 'value2', 'key3': 'value3'},
                      'section2': {'keyA': 'valueA', 'keyB': 'valueB', 'keyC': 'valueC'},
                      'section3': {'foo': 'x', 'bar': 'y', 'baz': 'z'}}

        self.assertRaises(NoSectionError, ConfigReader(tox_config).get_modernizer)

    def test_replaces_python_interpreters(self):
        self._assert_replaces_python_interpreters(self.config_file1)
        self._assert_replaces_python_interpreters(self.config_file2)

    def test_replaces_django_runners(self):
        self._assert_replaces_django_runners(self.config_file1)
        self._assert_replaces_django_runners(self.config_file2)

    def test_django_dependency_replaced(self):
        self._assert_django_dependencies_replaced(self.config_file1)
        self._assert_django_dependencies_replaced(self.config_file2)

    def test_adds_django_dependency(self):
        self._assert_adds_django_dependencies(self.config_file1)
        self._assert_adds_django_dependencies(self.config_file2)

    def tearDown(self):
        os.remove(self.config_file1)
        os.remove(self.config_file2)
