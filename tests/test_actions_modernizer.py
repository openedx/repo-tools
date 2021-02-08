"""
Tests for Github Actions Modernizer Script
"""
import os
import shutil
import uuid
from unittest import TestCase

from edx_repo_tools.codemods.django3 import GithubCIModernizer
from edx_repo_tools.utils import YamlLoader


class TestGithubActionsModernizer(TestCase):

    def setUp(self):
        self.test_file1 = self._setup_local_copy("sample_files/sample_ci_file.yml")
        self.test_file2 = self._setup_local_copy("sample_files/sample_ci_file_2.yml")
        self.test_file3 = self._setup_local_copy("sample_files/sample_ci_file_3.yml")

    @staticmethod
    def _setup_local_copy(file_name):
        current_directory = os.path.dirname(__file__)
        temp_file = os.path.join(current_directory, str(uuid.uuid4()) + ".yml")
        local_file = os.path.join(current_directory, file_name)
        shutil.copy2(local_file, temp_file)
        return temp_file

    @staticmethod
    def _get_updated_yaml_elements(file_path):
        modernizer = GithubCIModernizer(file_path)
        modernizer.modernize()
        yaml_loader = YamlLoader(file_path)
        return yaml_loader.elements

    def test_python_matrix_items(self):
        ci_elements = TestGithubActionsModernizer._get_updated_yaml_elements(self.test_file1)
        python_versions = ci_elements['jobs']['run_tests']['strategy']['matrix']['python-version']

        self.assertIsInstance(python_versions, list)
        self.assertNotIn('3.5', python_versions)

    def test_python_matrix_items_build_tag(self):
        ci_elements = TestGithubActionsModernizer._get_updated_yaml_elements(self.test_file3)
        python_versions = ci_elements['jobs']['build']['strategy']['matrix']['python-version']

        self.assertIsInstance(python_versions, list)
        self.assertNotIn('3.5', python_versions)

    def test_include_exclude_list(self):
        ci_elements = TestGithubActionsModernizer._get_updated_yaml_elements(self.test_file2)
        include_list = ci_elements['jobs']['run_tests']['strategy']['matrix'].get('include', {})
        exclude_list = ci_elements['jobs']['run_tests']['strategy']['matrix'].get('exclude', {})

        for item in list(include_list) + list(exclude_list):
            self.assertNotEqual(item['python-version'], '3.5')

    def tearDown(self):
        os.remove(self.test_file1)
        os.remove(self.test_file2)
        os.remove(self.test_file3)
