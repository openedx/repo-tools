import pytest
import re
import six

class OEP2(object):
    def check_does_openedx_yaml_exist(self, openedx_yaml):
        assert openedx_yaml is not None

    def check_is_owner_set_in_openedx_yaml(self, openedx_yaml):
        if openedx_yaml is None:
            pytest.xfail("No openedx.yaml file found")

        if not openedx_yaml.get('archived', False) == True:
            assert 'owner' in openedx_yaml and openedx_yaml.get('owner') != "MUST FILL IN OWNER"

    def check_is_nick_set_in_openedx_yaml(self, openedx_yaml):
        if openedx_yaml is None:
            pytest.xfail("No openedx.yaml file found")

        assert 'nick' in openedx_yaml

    def check_are_tags_set_in_openedx_yaml(self, openedx_yaml):
        if openedx_yaml is None:
            pytest.xfail("No openedx.yaml file found")

        assert 'tags' in openedx_yaml

    def check_are_oeps_properly_formatted_in_openedx_yaml(self, openedx_yaml):
        if openedx_yaml is None:
            pytest.xfail("No openedx.yaml file found")

        assert 'oeps' in openedx_yaml

        for key, value in openedx_yaml['oeps'].items():
            assert re.match(r'oep-\d+', key)
            assert isinstance(value, dict) or isinstance(value, bool)

            if isinstance(value, dict):
                if value.get('applicable', True):
                    assert 'state' in value
                    assert 'reason' in value
                    assert isinstance(value['state'], bool)
                    assert isinstance(value['reason'], six.string_types)
