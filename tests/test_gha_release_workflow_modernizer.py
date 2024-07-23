"""
Tests for GitHub Actions Modernizer Script
"""
import shutil
import uuid
from os.path import basename, dirname, join

from edx_repo_tools.codemods.node16 import GithubNodeReleaseWorkflowModernizer
from edx_repo_tools.utils import YamlLoader

NODE_JS_SETUP_ACTION_LIST = ['actions/setup-node@v2', 'actions/setup-node@v1']


def setup_local_dir(dirpath, tmpdir):
    current_directory = dirname(__file__)
    local_dir = join(current_directory, dirpath)
    fake_repo_path = tmpdir.mkdir(f"fake_repo_{uuid.uuid4()}")
    shutil.copytree(local_dir, fake_repo_path, dirs_exist_ok=True)
    return fake_repo_path

def get_updated_yaml_elements(file_path):
    modernizer = GithubNodeReleaseWorkflowModernizer(file_path)
    modernizer.modernize()
    yaml_loader = YamlLoader(file_path)
    return yaml_loader.elements


def test_add_node_env_step(tmpdir):
    node_env_step = None
    fake_repo_path = setup_local_dir('fake_repos/repo_with_nvmrc/',tmpdir)
    test_file = join(fake_repo_path, ".github/workflows/release.yml")
    ci_elements = get_updated_yaml_elements(test_file)
    for step in ci_elements['jobs']['release']['steps']:
        if 'name' in step and step['name'] == 'Setup Nodejs Env':
            node_env_step = step
    assert node_env_step['run'] == 'echo "NODE_VER=`cat .nvmrc`" >> $GITHUB_ENV'


def test_node_version_value(tmpdir):
    fake_repo_without_nvmrc_path = setup_local_dir('fake_repos/repo_without_nvmrc/',tmpdir)
    test_file = join(fake_repo_without_nvmrc_path, ".github/workflows/release.yml")
    ci_elements_without_rc_file_present = get_updated_yaml_elements(test_file)

    node_setup_step = None
    for step in ci_elements_without_rc_file_present['jobs']['release']['steps']:
        if 'uses' in step and step['uses'] in NODE_JS_SETUP_ACTION_LIST:
            node_setup_step = step

    assert node_setup_step['with']['node-version'] == 16

    fake_repo_with_nvmrc_path = setup_local_dir('fake_repos/repo_with_nvmrc/',tmpdir)
    test_file = join(fake_repo_with_nvmrc_path, ".github/workflows/release.yml")
    ci_elements_with_rc_file_present = get_updated_yaml_elements(test_file)

    node_setup_step = None
    for step in ci_elements_with_rc_file_present['jobs']['release']['steps']:
        if 'uses' in step and step['uses'] in NODE_JS_SETUP_ACTION_LIST:
            node_setup_step = step
    assert node_setup_step['with']['node-version'] == '${{ env.NODE_VER }}'
