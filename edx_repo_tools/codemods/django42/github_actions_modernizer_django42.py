"""
Modernizer for Github Actions CI Django 4.2 support
"""
from copy import deepcopy
import click
from edx_repo_tools.utils import YamlLoader

ALLOWED_DJANGO_VERSIONS = ['django32', 'django42']


class GithubCIModernizer(YamlLoader):
    def __init__(self, file_path):
        super().__init__(file_path)

    def _update_django_in_matrix(self):
        django_versions = list()
        matrix_elements = dict()
        section_key = None

        for key in ['build', 'tests', 'run_tests', 'run_quality', 'pytest']:
            if key in self.elements['jobs']:
                section_key = key
                matrix_elements = deepcopy(self.elements['jobs'][section_key]['strategy']['matrix'])

        for key, value in matrix_elements.items():
            if key == 'django-version':
                django_versions = value
                django_versions.extend(filter(
                    lambda version: version not in value, ALLOWED_DJANGO_VERSIONS))
        if not section_key:
            return
        if django_versions:
            self.elements['jobs'][section_key]['strategy']['matrix']['django-version'] = django_versions

    def _update_github_actions(self):
        self._update_django_in_matrix()

    def modernize(self):
        self._update_github_actions()
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
