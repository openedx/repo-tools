import os
import shutil

from ruamel.yaml import YAML

from edx_repo_tools.modernize_openedx_yaml import YamlModernizer


def setup_local_copy(tmpdir):
    sample_yam_file = os.path.join(os.path.dirname(__file__), "sample_openedx.yaml")
    temp_file_path = str(tmpdir.join('test-openedx.yaml'))
    shutil.copy2(sample_yam_file, temp_file_path)
    return temp_file_path


def load_yaml(sample_yam_file):
    with open(sample_yam_file) as file_stream:
        return YAML().load(file_stream)


def test_travis_modernizer(tmpdir):
    test_yaml_file = setup_local_copy(tmpdir)
    modernizer = YamlModernizer(test_yaml_file)
    modernizer.modernize()
    updated_yaml = load_yaml(test_yaml_file)
    assert 'owner' not in updated_yaml.keys()
    assert 'supporting_teams' not in updated_yaml.keys()
    assert 'track_pulls' not in updated_yaml.keys()
    assert 'track-pulls' not in updated_yaml.keys()
