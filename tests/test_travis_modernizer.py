import os
import re
import shutil
import uuid
from unittest import TestCase

from edx_repo_tools.codemods.django3 import TravisModernizer, DJANGO_PATTERN
from edx_repo_tools.utils import YamlLoader


class TestTravisModernizer(TestCase):

    def setUp(self):
        self.test_file1 = self._setup_local_copy("test_travis.yml")
        self.test_file2 = self._setup_local_copy("test_travis_2.yml")

    @staticmethod
    def _setup_local_copy(file_name):
        current_directory = os.path.dirname(__file__)
        temp_file = os.path.join(current_directory, str(uuid.uuid4()) + ".yml")
        local_file = os.path.join(current_directory, file_name)
        shutil.copy2(local_file, temp_file)
        return temp_file

    @staticmethod
    def _get_updated_yaml_elements(file_path):
        modernizer = TravisModernizer(file_path)
        modernizer.modernize()
        yaml_loader = YamlLoader(file_path)
        return yaml_loader.elements

    def test_python_env_items(self):
        travis_elements = TestTravisModernizer._get_updated_yaml_elements(self.test_file1)
        python_versions = travis_elements.get("python")

        self.assertIsInstance(python_versions, list)
        self.assertTrue(len(python_versions), 1)
        python_version = python_versions[0]

        self.assertEqual(str(python_version), '3.8')

    def test_python_matrix_items(self):
        travis_elements = TestTravisModernizer._get_updated_yaml_elements(self.test_file2)
        python_versions = [matrix_item for matrix_item in travis_elements.get("matrix").get("include")
                           if 'python' in matrix_item.keys()]

        self.assertIsInstance(python_versions, list)
        self.assertTrue(len(python_versions), 1)
        python_version = python_versions[0].get('python')

        self.assertEqual(python_version, '3.8')

    def test_django_env_items(self):
        travis_elements = TestTravisModernizer._get_updated_yaml_elements(self.test_file1)
        django_envs = [django_env_item for django_env_item in travis_elements.get("env")
                       if re.search(DJANGO_PATTERN, django_env_item)]
        self.assertIsInstance(django_envs, list)
        self.assertTrue(len(django_envs), 3)

        self.assertTrue(any("django22" in django_env for django_env in django_envs))
        self.assertTrue(any("django30" in django_env for django_env in django_envs))
        self.assertTrue(any("django31" in django_env for django_env in django_envs))

    def test_django_matrix_items(self):
        travis_elements = TestTravisModernizer._get_updated_yaml_elements(self.test_file2)
        django_matrix_envs = [matrix_item for matrix_item in travis_elements.get("matrix").get("include")
                              if re.search(DJANGO_PATTERN, matrix_item.get("env"))]

        self.assertIsInstance(django_matrix_envs, list)
        self.assertTrue(len(django_matrix_envs), 3)

        django_envs = [matrix_item.get("env") for matrix_item in django_matrix_envs]

        self.assertTrue(any("django22" in django_env for django_env in django_envs))
        self.assertTrue(any("django30" in django_env for django_env in django_envs))
        self.assertTrue(any("django31" in django_env for django_env in django_envs))

    def tearDown(self):
        os.remove(self.test_file1)
        os.remove(self.test_file2)
