import pytest
import re


def test_openedx_yaml(openedx_yaml):
    assert openedx_yaml is not None

def test_owner(openedx_yaml):
    if openedx_yaml is None:
        pytest.skip("No openedx.yaml file found")

    assert openedx_yaml.get('owner') != "MUST FILL IN OWNER"

def test_nick(openedx_yaml):
    if openedx_yaml is None:
        pytest.skip("No openedx.yaml file found")

    assert 'nick' in openedx_yaml

def test_tags(openedx_yaml):
    if openedx_yaml is None:
        pytest.skip("No openedx.yaml file found")

    assert 'tags' in openedx_yaml

def test_oeps(openedx_yaml):
    if openedx_yaml is None:
        pytest.skip("No openedx.yaml file found")

    assert 'oeps' in openedx_yaml

    for key, value in openedx_yaml['oeps'].items():
        assert re.match(r'oep-\d+', key)
        assert isinstance(value, dict) or isinstance(value, bool)

        if isinstance(value, dict):
            assert 'state' in value
            assert 'reason' in value
            assert isinstance(value['state'], bool)
            assert isinstance(value['reason'], basestring)

