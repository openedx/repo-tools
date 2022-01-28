"""
Tests for setup file modernizer
"""
import os
import shutil
from os.path import basename, dirname, join

from edx_repo_tools.codemods.django3.setup_file_modernizer import SetupFileModernizer


def setup_local_copy(filepath, tmpdir):
    current_directory = dirname(__file__)
    local_file = join(current_directory, filepath)
    temp_file_path = str(join(tmpdir, basename(filepath)))
    shutil.copy2(local_file, temp_file_path)
    return temp_file_path

def test_remove_existing_classifiers(tmpdir):
    """
    Test the case where old classifiers are removed
    """
    test_file = setup_local_copy("sample_files/sample_setup_file.py", tmpdir)
    setup_file_modernizer = SetupFileModernizer()
    file_data = open(test_file).read()
    updated_file_data = setup_file_modernizer._remove_outdated_classifiers(file_data)
    assert "'Framework :: Django :: 3.1'" not in updated_file_data
    assert "'Framework :: Django :: 3.0'" not in updated_file_data
    assert "'Framework :: Django :: 2.2'" not in updated_file_data
    assert "'Framework :: Django :: 3.2'" in updated_file_data

def test_add_new_classifiers(tmpdir):
    """
    Test the case where new classifiers are added
    """
    test_file = setup_local_copy("sample_files/sample_setup_file.py", tmpdir)
    setup_file_modernizer = SetupFileModernizer()
    file_data = open(test_file).read()
    updated_file_data = setup_file_modernizer._add_new_classifiers(file_data)
    assert "'Framework :: Django :: 4.0'" in updated_file_data
