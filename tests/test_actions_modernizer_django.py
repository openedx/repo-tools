"""
Tests for Github Actions Django Modernizer Script
"""
import os
import shutil
from os.path import basename, dirname, join

from edx_repo_tools.codemods.python312 import GithubCIModernizer
from edx_repo_tools.utils import YamlLoader


def setup_local_copy(filepath, tmpdir):
    current_directory = dirname(__file__)
    local_file = join(current_directory, filepath)
    temp_file_path = str(join(tmpdir, basename(filepath)))
    shutil.copy2(local_file, temp_file_path)
    return temp_file_path


def get_updated_yaml_elements(file_path):
    modernizer = GithubCIModernizer(file_path)
    modernizer.modernize()
    yaml_loader = YamlLoader(file_path)
    return yaml_loader.elements


def test_matrix_items(tmpdir):
    """
    Test the scenario where django env is present in the tox-envs within a single job workflow.
    """
    test_file = setup_local_copy("sample_files/sample_ci_file.yml", tmpdir)
    ci_elements = get_updated_yaml_elements(test_file)
    tox_envs = ci_elements['jobs']['run_tests']['strategy']['matrix']['toxenv']

    assert 'django32' not in tox_envs
    assert 'django42' in tox_envs


def test_matrix_items_multiple_jobs(tmpdir):
    """
    Test the scenarios with multiple jobs including/excluding django in test tox-envs.
    """
    test_file = setup_local_copy("sample_files/sample_ci_file_multiple_jobs.yml", tmpdir)
    ci_elements = get_updated_yaml_elements(test_file)

    # test the case with django env present in one job
    job1_tox_envs = ci_elements['jobs']['build']['strategy']['matrix']['tox-env']
    assert 'django32' not in job1_tox_envs
    assert 'django42' in job1_tox_envs

    # test the case with django env present in second job
    job2_tox_envs = ci_elements['jobs']['django_test']['strategy']['matrix']['django-version']
    assert 'django32' not in job2_tox_envs
    assert 'django42' in job2_tox_envs

    # test the case with no django env present in third job.
    job3_tox_envs = ci_elements['jobs']['test']['strategy']['matrix']['tox']
    assert 'django42' in job3_tox_envs

def test_include_exclude_list(tmpdir):
    """
    Test the scenario with job's matrix having include, exclude sections
    """
    test_file = setup_local_copy("sample_files/sample_ci_file_5.yml", tmpdir)
    ci_elements = get_updated_yaml_elements(test_file)
    include_list = ci_elements['jobs']['run_tests']['strategy']['matrix'].get('include', {})
    exclude_list = ci_elements['jobs']['run_tests']['strategy']['matrix'].get('exclude', {})

    for item in list(include_list) + list(exclude_list):
        if 'django-version' in item:
            assert item['django-version'] != '3.2'
        if 'toxenv' in item:
            assert item['toxenv'] != 'django42'
