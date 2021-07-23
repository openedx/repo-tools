"""
Django Matrix Modernizer for Github Actions CI
"""
import re
from copy import deepcopy

import click

from edx_repo_tools.utils import YamlLoader

DJANGO_ENV_PATTERN = r"django[0-3][0-2][0-2]?"
ALLOWED_DJANGO_ENVS = ['django22', 'django30', 'django31', 'django32']


class GithubCIDjangoModernizer(YamlLoader):
    def __init__(self, file_path):
        super().__init__(file_path)
        self.yml_instance.default_flow_style = None
        self.yml_instance.indent(mapping=2, sequence=2, offset=0)

    def _update_matrix_items(self, job_name, matrix_item_name, matrix_item):
        if not isinstance(matrix_item, list):
            return

        has_django_env = any(
            re.match(DJANGO_ENV_PATTERN, item) for item in matrix_item
        )
        if not has_django_env:
            return
        non_django_matrix_items = [item for item in matrix_item if not re.match(DJANGO_ENV_PATTERN, item)]
        updated_matrix_items = non_django_matrix_items + ALLOWED_DJANGO_ENVS
        self.elements['jobs'][job_name]['strategy']['matrix'][matrix_item_name] = updated_matrix_items

    def _update_django_matrix_items(self, job_name, job):
        matrices = job.get('strategy').get('matrix').items()
        for matrix_item_key, matrix_item in matrices:
            self._update_matrix_items(job_name, matrix_item_key, matrix_item)

    def _update_job_matrices(self):
        for job_name, job in self.elements.get('jobs').items():
            self._update_django_matrix_items(job_name, job)

    def modernize(self):
        self._update_job_matrices()
        self.update_yml_file()


@click.command()
@click.option(
    '--path', default='.github/workflows/ci.yml',
    help="Path to default CI workflow file")
def main(path):
    modernizer = GithubCIDjangoModernizer(path)
    modernizer.modernize()


if __name__ == '__main__':
    main()
