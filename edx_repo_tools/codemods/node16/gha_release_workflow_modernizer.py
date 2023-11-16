"""
Node modernizer for Github CI release workflow
"""

from copy import deepcopy
from os.path import exists
from pathlib import Path

import click
from ruamel.yaml import YAML

from edx_repo_tools.utils import YamlLoader

NODE_RELEASE_VERSION = 16
NODE_JS_SETUP_ACTION_LIST = ['actions/setup-node@v2', 'actions/setup-node@v1']
FETCH_NODE_VERSION_STEP = """name: 'Setup Nodejs Env'\nrun: 'echo "NODE_VER=`cat .nvmrc`" >> $GITHUB_ENV'\n"""

class GithubNodeReleaseWorkflowModernizer(YamlLoader):
    def __init__(self, release_workflow_file_path):
        super().__init__(release_workflow_file_path)

    def _does_nvmrc_exists(self):
        target_file = Path(self.file_path).resolve().parents[2]
        target_file = str(target_file) + '/.nvmrc'
        return exists(target_file)

    def _add_setup_nodejs_env_step(self, step_elements, step_index):
        if self._does_nvmrc_exists():
            yaml = YAML()
            fetch_node_version_step = yaml.load(FETCH_NODE_VERSION_STEP)
            step_elements.insert(
                step_index, fetch_node_version_step)
        return step_elements

    def _update_node_version(self, step_elements, step_index):
        if self._does_nvmrc_exists():
            step_elements[step_index]['with']['node-version'] = "${{ env.NODE_VER }}"
        else:
            step_elements[step_index]['with']['node-version'] = 16
        return step_elements

    def _update_job_steps(self, job_name, job):
        steps = job.get('steps')
        updated_job_steps = None
        if not steps:
            return
        for step in steps:
            if 'uses' in step and step['uses'] in NODE_JS_SETUP_ACTION_LIST:
                step_index = self.elements['jobs'][job_name]['steps'].index(step)
                job_steps = deepcopy(self.elements['jobs'][job_name]['steps'])
                job_steps = self._update_node_version(job_steps, step_index)
                job_steps = self._add_setup_nodejs_env_step(job_steps, step_index)

                updated_job_steps = job_steps
        return updated_job_steps


    def _update_job(self):
        jobs = self.elements.get('jobs')
        if 'release' in jobs:
            updated_job = self._update_job_steps(
                'release', self.elements['jobs']['release'])
            self.elements['jobs']['release']['steps'] = updated_job

    def modernize(self):
        self._update_job()
        self.update_yml_file()


@click.command()
@click.option(
    '--workflow_path', default='./.github/workflows/release.yml',
    help="Path to release workflow file")
def main(workflow_path):
    modernizer = GithubNodeReleaseWorkflowModernizer(workflow_path)
    modernizer.modernize()


if __name__ == '__main__':
    main()
