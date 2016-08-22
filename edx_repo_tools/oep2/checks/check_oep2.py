import pytest
import re

def check_openedx_yaml(openedx_yaml):
    assert openedx_yaml is not None

def check_owner(openedx_yaml):
    if openedx_yaml is None:
        pytest.xfail("No openedx.yaml file found")

    assert openedx_yaml.get('owner') != "MUST FILL IN OWNER"

def check_nick(openedx_yaml):
    if openedx_yaml is None:
        pytest.xfail("No openedx.yaml file found")

    assert 'nick' in openedx_yaml

def check_tags(openedx_yaml):
    if openedx_yaml is None:
        pytest.xfail("No openedx.yaml file found")

    assert 'tags' in openedx_yaml

def check_oeps(openedx_yaml):
    if openedx_yaml is None:
        pytest.xfail("No openedx.yaml file found")

    assert 'oeps' in openedx_yaml

    for key, value in openedx_yaml['oeps'].items():
        assert re.match(r'oep-\d+', key)
        assert isinstance(value, dict) or isinstance(value, bool)

        if isinstance(value, dict):
            assert 'state' in value
            assert 'reason' in value
            assert isinstance(value['state'], bool)
            assert isinstance(value['reason'], basestring)

