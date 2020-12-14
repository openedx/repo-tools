import re
from copy import deepcopy

import click

from edx_repo_tools.utils import YamlLoader

ALLOWED_PYTHON_VERSIONS = '3.8'

DEPRECATED_DJANGO_VERSIONS_PATTERN = r"django111|django20|django21"
ALLOWED_DJANGO_VERSIONS_PATTERN = r"django22|django30|django31"

DJANGO_PATTERN = r"django[0-3][0-2][0-2]?"

ALLOWED_DJANGO_VERSIONS = ['django22', 'django30', 'django31']


class TravisModernizer(YamlLoader):
    def __init__(self, file_path):
        super().__init__(file_path)

    def _update_python_dict(self):
        python_versions = self.elements.get('python', None)
        if python_versions is None:
            return
        self.elements['python'] = [ALLOWED_PYTHON_VERSIONS]

    def _update_matrix_python_versions(self):
        matrix_elements = self.elements.get("matrix", {}).get("include")
        if matrix_elements is None:
            return
        has_python_matrix = any(matrix_item.get("python") is not None for matrix_item in matrix_elements)
        if not has_python_matrix:
            return
        non_python_matrix_elements = []
        python_matrix_items = []
        for matrix_element in matrix_elements:
            if 'python' not in matrix_element.keys():
                non_python_matrix_elements.append(matrix_element)
                continue
            python_matrix_item = deepcopy(matrix_element)
            python_matrix_item['python'] = ALLOWED_PYTHON_VERSIONS
            python_matrix_items.append(python_matrix_item)
            break
        self.elements["matrix"]["include"] = non_python_matrix_elements + python_matrix_items

    @staticmethod
    def _get_updated_django_matrix_items(django_matrix_item):
        updated_django_matrix_items = []
        for django_version in ALLOWED_DJANGO_VERSIONS:
            django_matrix_item_clone = deepcopy(django_matrix_item)
            django_matrix_item_clone["env"] = re.sub(DJANGO_PATTERN, django_version, django_matrix_item_clone["env"])
            updated_django_matrix_items.append(django_matrix_item_clone)
        return updated_django_matrix_items

    @staticmethod
    def _get_updated_django_envs(django_env_item):
        updated_django_env_items = []
        for django_version in ALLOWED_DJANGO_VERSIONS:
            django_env_item = re.sub(DJANGO_PATTERN, django_version, django_env_item)
            updated_django_env_items.append(django_env_item)
        return updated_django_env_items

    def _update_django_envs(self):
        env_elements = self.elements.get("env")
        if env_elements is None:
            return
        has_django_env = any(re.search(DJANGO_PATTERN, env_item) for env_item in env_elements)
        if not has_django_env:
            return
        django_env_item = [django_env_item for django_env_item in env_elements
                           if re.search(DJANGO_PATTERN, django_env_item)][0]
        non_django_env_items = [env_item for env_item in env_elements
                                if not re.search(DJANGO_PATTERN, env_item)]
        self.elements["env"] = non_django_env_items + TravisModernizer._get_updated_django_envs(django_env_item)

    def _update_django_matrix_envs(self):
        matrix_items = self.elements.get("matrix", {}).get("include", [])
        if not matrix_items:
            return
        has_django_env = any(re.search(DJANGO_PATTERN, matrix_item.get('env', '')) for matrix_item in matrix_items)
        if not has_django_env:
            return
        django_matrix_element = [matrix_item for matrix_item in matrix_items
                                 if re.search(DJANGO_PATTERN, matrix_item.get("env", ""))][0]
        non_django_matrix_items = [matrix_item for matrix_item in matrix_items
                                   if not re.search(DJANGO_PATTERN, matrix_item.get("env", ""))]
        self.elements["matrix"]["include"] = (non_django_matrix_items +
                                              TravisModernizer._get_updated_django_matrix_items(django_matrix_element))

    def _update_python_versions(self):
        self._update_python_dict()
        self._update_matrix_python_versions()

    def _update_django_versions(self):
        self._update_django_envs()
        self._update_django_matrix_envs()

    def modernize(self):
        self._update_python_versions()
        self._update_django_versions()
        self.update_yml_file()


@click.command()
@click.option(
    '--path', default='.travis.yml',
    help="Path to target travis config file")
def main(path):
    modernizer = TravisModernizer(path)
    modernizer.modernize()


if __name__ == '__main__':
    main()
