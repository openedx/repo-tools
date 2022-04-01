"""
Node Modernizer for Github Actions CI
"""
import click
from copy import deepcopy

from edx_repo_tools.utils import YamlLoader

ALLOWED_NODE_VERSIONS = [16]
ALLOWED_NPM_VERSION = '8.x.x'


class GithubCiNodeModernizer(YamlLoader):
    def __init__(self, file_path):
        super().__init__(file_path)

    def _add_new_matrix(self, job_name):
        self.elements['jobs'][job_name]['strategy'] = {'matrix': {'node': ALLOWED_NODE_VERSIONS}}
        self.elements['jobs'][job_name].move_to_end('strategy', last=False)
        self.elements['jobs'][job_name].move_to_end('runs-on', last=False)
        if 'name' in self.elements['jobs'][job_name]:
            self.elements['jobs'][job_name].move_to_end('name', last=False)

    def _update_existing_matrix(self, job_name):
        self.elements['jobs'][job_name]['strategy']['matrix']['node'] = ALLOWED_NODE_VERSIONS

    def _update_strategy_matrix(self, job_name):
        if 'strategy' in self.elements['jobs'][job_name] and 'matrix' in self.elements['jobs'][job_name]['strategy']:
            self._update_existing_matrix(job_name)
        else:
            self._add_new_matrix(job_name)

    def _update_node_version(self, job_name, step):
        step_index = self.elements['jobs'][job_name]['steps'].index(step)
        self.elements['jobs'][job_name]['steps'][step_index]['with']['node-version'] = '${{ matrix.node }}'

    def _update_npm_version(self, job_name, step):
        step_index = self.elements['jobs'][job_name]['steps'].index(step)
        self.elements['jobs'][job_name]['steps'][step_index]['run'] = 'npm i -g npm@'+ALLOWED_NPM_VERSION

    def _update_job_steps(self, job_name, job):
        steps = job.get('steps')
        if not steps:
            return
        for step in steps:
            if 'name' in step and step['name'] == 'Setup Nodejs':
                self._update_node_version(job_name, step)
            elif 'name' in step and step['name'] == 'Setup npm':
                self._update_npm_version(job_name, step)

    def _update_job_name(self, job_name, job):
        self.elements['jobs']['tests'] = deepcopy(job)
        self.elements['jobs'].move_to_end('tests', last=False)
        self.elements['jobs'].pop(job_name)

    def _update_job(self):
        jobs = self.elements.get('jobs')
        if 'tests' not in jobs and 'build' in jobs:
            self._update_job_name('build', self.elements['jobs']['build'])
        if 'tests' in jobs:
            self._update_strategy_matrix('tests')
            self._update_job_steps('tests', self.elements['jobs']['tests'])

    def modernize(self):
        self._update_job()
        self.update_yml_file()


@click.command()
@click.option(
    '--path', default='./.github/workflows/ci.yml',
    help="Path to default CI workflow file")
def main(path):
    modernizer = GithubCiNodeModernizer(path)
    modernizer.modernize()


if __name__ == '__main__':
    main()
