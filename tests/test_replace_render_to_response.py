"""Tests for replace_render_to_response script"""
import subprocess

import os
import shutil


def setup_local_copy(tmpdir, path):
    sample_file = os.path.join(os.path.dirname(__file__), "sample_files", path)
    temp_file_path = str(tmpdir.join('sample_render_to_response_tmp.py'))
    shutil.copy2(sample_file, temp_file_path)
    return temp_file_path


def test_replace_script(tmpdir):
    """
    Test replace script on a file to make sure it is renaming it properly and
    also adding request parameter to updated function call
    """
    sample_file_path = setup_local_copy(tmpdir, "sample_render_to_response.py")
    with open(sample_file_path) as sample_file:
        sample_code = sample_file.read()
        assert "render_to_response" in sample_code
        assert "render_to_response(request, " not in sample_code
        assert "render(request, " not in sample_code
    subprocess.call(['replace_render_to_response', sample_file_path])
    with open(sample_file_path) as sample_file:
        sample_code = sample_file.read()
        assert "render_to_response" not in sample_code
        assert "render" in sample_code
        # Adding request parameter to function call
        assert "render(request, " in sample_code


def test_replace_script_avoid_non_django_version(tmpdir):
    """
    Test replace script on the file in which function name shouldn't be changed
    as it is being imported from some local directory instead of django.shortcuts
    """
    sample_file_path = setup_local_copy(tmpdir, "sample_render_to_response_2.py")
    with open(sample_file_path) as sample_file:
        sample_code = sample_file.read()
        assert "render_to_response" in sample_code
        assert "render(request, " not in sample_code
    subprocess.call(['replace_render_to_response', sample_file_path])
    with open(sample_file_path) as sample_file:
        sample_code = sample_file.read()
        # Shouldn't replace render_to_response in this file
        assert "render_to_response" in sample_code
        assert "render(request, " not in sample_code
