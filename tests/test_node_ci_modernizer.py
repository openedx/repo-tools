"""
Tests for Github Actions Modernizer Script
"""
import shutil
from os.path import dirname, basename, join

from edx_repo_tools.codemods.node16 import GithubCiNodeModernizer
from edx_repo_tools.utils import YamlLoader


def setup_local_copy(filepath, tmpdir):
    current_directory = dirname(__file__)
    local_file = join(current_directory, filepath)
    temp_file_path = str(join(tmpdir, basename(filepath)))
    shutil.copy2(local_file, temp_file_path)
    return temp_file_path


def get_updated_yaml_elements(file_path):
    modernizer = GithubCiNodeModernizer(file_path)
    modernizer.modernize()
    yaml_loader = YamlLoader(file_path)
    return yaml_loader.elements


def test_node_version_value(tmpdir):
    test_file = setup_local_copy("sample_files/sample_node_ci.yml", tmpdir)
    ci_elements = get_updated_yaml_elements(test_file)

    node_setup_step = None
    for step in ci_elements['jobs']['tests']['steps']:
        if step['name'] == 'Setup Nodejs':
            node_setup_step = step

    assert '${{ matrix.node }}' in node_setup_step['with']['node-version']


def test_npm_version_value(tmpdir):
    test_file = setup_local_copy("sample_files/sample_node_ci.yml", tmpdir)
    ci_elements = get_updated_yaml_elements(test_file)

    npm_setup_step = None
    for step in ci_elements['jobs']['tests']['steps']:
        if step['name'] == 'Setup npm':
            npm_setup_step = step

    assert '8.x.x' in npm_setup_step['run']


def test_job_name(tmpdir):
    test_file = setup_local_copy("sample_files/sample_node_ci.yml", tmpdir)
    ci_elements = get_updated_yaml_elements(test_file)

    assert 'tests' in ci_elements['jobs']


def test_add_matrix_items(tmpdir):
    test_file = setup_local_copy("sample_files/sample_node_ci.yml", tmpdir)
    ci_elements = get_updated_yaml_elements(test_file)

    assert 16 in ci_elements['jobs']['tests']['strategy']['matrix']['node']


def test_update_matrix_items(tmpdir):
    test_file = setup_local_copy("sample_files/sample_node_ci2.yml", tmpdir)
    ci_elements = get_updated_yaml_elements(test_file)

    assert 16 in ci_elements['jobs']['tests']['strategy']['matrix']['node']
