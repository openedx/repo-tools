"""
Github Actions CI Modernizer to add Python 3.12 and drop Django 3.2 testing
"""
import os
from copy import deepcopy
import click
from edx_repo_tools.utils import YamlLoader

TO_BE_REMOVED_PYTHON = ['3.5', '3.6', '3.7']
ALLOWED_PYTHON_VERSIONS = ['3.8', '3.12']

ALLOWED_DJANGO_VERSIONS = ['4.2', 'django42']
DJANGO_ENV_TO_ADD = ['django42']
DJANGO_ENV_TO_REMOVE = ['django32', 'django40', 'django41']


class GithubCIModernizer(YamlLoader):
    def __init__(self, file_path):
        super().__init__(file_path)

    def _update_python_and_django_in_matrix(self):
        django_versions = list()
        python_versions = list()
        matrix_elements = dict()


        for section_key in self.elements['jobs']:
            matrix_elements = deepcopy(self.elements['jobs'][section_key]['strategy']['matrix'])

            for key, value in matrix_elements.items():
                if key == 'django-version':
                    for dj_version in DJANGO_ENV_TO_ADD:
                        if dj_version not in value:
                            value.append(dj_version)
                    django_versions = list(filter(lambda version: version in ALLOWED_DJANGO_VERSIONS, value))
                    if django_versions:
                        self.elements['jobs'][section_key]['strategy']['matrix'][key] = django_versions

                if key in ['tox', 'toxenv', 'tox-env']:
                    for dj_env in DJANGO_ENV_TO_ADD:
                        if dj_env not in value:
                            value.append(dj_env)
                    tox_envs = list(filter(lambda version: version not in DJANGO_ENV_TO_REMOVE, value))
                    if tox_envs:
                        self.elements['jobs'][section_key]['strategy']['matrix'][key] = tox_envs

                if key == 'python-version':
                    for version in ALLOWED_PYTHON_VERSIONS:
                        if version not in value:
                            value.append(version)
                    python_versions = list(filter(lambda version: version not in TO_BE_REMOVED_PYTHON, value))
                    if python_versions:
                        self.elements['jobs'][section_key]['strategy']['matrix'][key] = python_versions
                    else:
                        del self.elements['jobs'][section_key]['strategy']['matrix'][key]

                elif key in ['include', 'exclude']:
                    allowed_python_vers = list()
                    for item in value:
                        if item['python-version'] not in TO_BE_REMOVED_PYTHON:
                            allowed_python_vers.append(item)

                    if len(allowed_python_vers):
                        self.elements['jobs'][section_key]['strategy']['matrix'][key] = allowed_python_vers
                    else:
                        del self.elements['jobs'][section_key]['strategy']['matrix'][key]
    

    def _update_github_actions(self):
        self._update_python_and_django_in_matrix()

    def modernize(self):
        self._update_github_actions()
        self.update_yml_file()


@click.command()
@click.option(
    '--path', default='.github/workflows/ci.yml',
    help="Path to default CI workflow file")
def main(path):
    if os.path.exists(path):
        modernizer = GithubCIModernizer(path)
        modernizer.modernize()
    else:
        print("ci.yml not found on specified path")


if __name__ == '__main__':
    main()
