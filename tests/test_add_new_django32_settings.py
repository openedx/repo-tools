"""
Tests for new django32 settings codemod
"""
import os
import shutil
from os.path import dirname, basename, join
from edx_repo_tools.codemods.django3.add_new_django32_settings import SettingsModernizer

def setup_local_copy(filepath, tmpdir):
    current_directory = dirname(__file__)
    local_file = join(current_directory, filepath)
    temp_file_path = str(join(tmpdir, basename(filepath)))
    shutil.copy2(local_file, temp_file_path)
    return temp_file_path

def test_update_existing_hashing_algorithm(tmpdir):
    """
    Test the case where an old hashing algorithm is already present in the settings
    """
    test_file = setup_local_copy("sample_files/sample_django_settings_2.py", tmpdir)
    setting_modernizer = SettingsModernizer(setting_path=test_file, is_service=True)
    setting_modernizer.update_hash_algorithm()
    with open(test_file) as test_setting_file:
        target_algorithm = f"{setting_modernizer.DEFAULT_ALGORITHM_KEY} = '{setting_modernizer.NEW_HASHING_ALGORITHM}'"
        assert target_algorithm in test_setting_file.read()

def test_add_new_hashing_algorithm(tmpdir):
    """
    Test the case where no hashing algorithm is present in the settings
    """
    test_file = setup_local_copy("sample_files/sample_django_settings.py", tmpdir)
    setting_modernizer = SettingsModernizer(setting_path=test_file, is_service=True)
    setting_modernizer.update_hash_algorithm()
    with open(test_file) as test_setting_file:
        target_algorithm = f"{setting_modernizer.DEFAULT_ALGORITHM_KEY} = '{setting_modernizer.NEW_HASHING_ALGORITHM}'"
        assert target_algorithm in test_setting_file.read()

def test_update_existing_auto_field(tmpdir):
    """
    Test the case where an old value of auto field is present in the settings
    """
    test_file = setup_local_copy("sample_files/sample_django_settings_2.py", tmpdir)
    setting_modernizer = SettingsModernizer(setting_path=test_file, is_service=True)
    setting_modernizer.update_auto_field()
    with open(test_file) as test_setting_file:
        target_field = f"{setting_modernizer.DEFAULT_FIELD_KEY} = '{setting_modernizer.NEW_AUTO_FIELD}'"
        assert target_field in test_setting_file.read()

def test_add_new_auto_field(tmpdir):
    """
    Test the case where no auto field value is present in the settings
    """
    test_file = setup_local_copy("sample_files/sample_django_settings.py", tmpdir)
    setting_modernizer = SettingsModernizer(setting_path=test_file, is_service=True)
    setting_modernizer.update_auto_field()
    with open(test_file) as test_setting_file:
        target_field = f"{setting_modernizer.DEFAULT_FIELD_KEY} = '{setting_modernizer.NEW_AUTO_FIELD}'"
        assert target_field in test_setting_file.read()

def test_add_new_context_processor(tmpdir):
    """
    Test the case where no request context_processor is present in the settings
    """
    test_file = setup_local_copy("sample_files/sample_django_settings.py", tmpdir)
    setting_modernizer = SettingsModernizer(setting_path=test_file, is_service=True)
    setting_modernizer.update_context_processors()
    with open(test_file) as test_setting_file:
        assert setting_modernizer.NEW_PROCESSOR in test_setting_file.read()
