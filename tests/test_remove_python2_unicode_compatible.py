"""
Tests for verifying the output of the script edx_repo_tools/codemods/django3/remove_python2_unicode_compatible.py
"""
import os
from unittest import TestCase
import shutil
import uuid
import subprocess
from edx_repo_tools.codemods.django3 import remove_python2_unicode_compatible


def setup_local_copy(tmpdir):
    """
    Setup local copy of the sample file for tests
    """
    sample_test_file = os.path.join(os.path.dirname(__file__), "sample_files/sample_python2_unicode_removal.py")
    temp_file_path = str(tmpdir.join('test-python2-unicode.py'))
    shutil.copy2(sample_test_file, temp_file_path)
    return temp_file_path


def test_python2_unicode_compatible_removed(tmpdir):
    """
    Test the script on a sample file to make sure it is removing python_2_unicode_compatible imports and decorators.
    """
    sample_file_path = setup_local_copy(tmpdir)
    with open(sample_file_path) as sample_file:
        sample_code = sample_file.read()
        assert "python_2_unicode_compatible" in sample_code
    remove_python2_unicode_compatible.run_removal_query(sample_file_path)
    with open(sample_file_path) as sample_file:
        sample_code = sample_file.read()
        assert "python_2_unicode_compatible" not in sample_code
