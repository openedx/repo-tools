"""
Modernizer for Github Actions CI
"""
from copy import deepcopy

import click

from edx_repo_tools.utils import YamlLoader

TO_BE_REMOVED_PYTHON = ['3.5']
ALLOWED_PYTHON_VERSIONS = ['3.6', '3.7', '3.8']


class GithubCIModernizer(YamlLoader):
    def __init__(self, file_path):
        super().__init__(file_path)
        self.yml_instance.default_flow_style = None
        self.yml_instance.indent(mapping=2, sequence=2, offset=0)

    def _update_matrix(self):

        python_versions = list()
        matrix_elements = dict()
        section_key = None

        for key in ['build', 'tests', 'run_tests', 'run_quality']:
            if key in self.elements['jobs']:
                section_key = key
                matrix_elements = deepcopy(self.elements['jobs'][section_key]['strategy']['matrix'])

        for key, value in matrix_elements.items():
            if key == 'python-version':
                python_versions.extend(filter(
                    lambda version: version in ALLOWED_PYTHON_VERSIONS, value))
            elif key in ['include', 'exclude']:
                without_python35 = list()
                for item in value:
                    if item['python-version'] not in TO_BE_REMOVED_PYTHON:
                        without_python35.append(item)

                if len(without_python35):
                    self.elements['jobs'][section_key]['strategy']['matrix'][key] = without_python35
                else:
                    del self.elements['jobs'][section_key]['strategy']['matrix'][key]

        self.elements['jobs'][section_key]['strategy']['matrix']['python-version'] = python_versions

    def _update_python_versions(self):
        self._update_matrix()

    def modernize(self):
        self._update_python_versions()
        self.update_yml_file()


@click.command()
@click.option(
    '--path', default='.github/workflows/ci.yml',
    help="Path to default CI workflow file")
def main(path):
    modernizer = GithubCIModernizer(path)
    modernizer.modernize()


if __name__ == '__main__':
    main()
