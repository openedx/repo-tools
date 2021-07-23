import pytest

def check_is_oep_explicitly_satisfied(openedx_yaml, oep):

    if openedx_yaml is None:
        pytest.xfail("No openedx.yaml found")

    if 'oeps' not in openedx_yaml:
        pytest.xfail("No 'oeps' key in openedx.yaml")

    oep_key = f'oep-{oep}'

    assert oep_key in openedx_yaml['oeps']

    oep_value = openedx_yaml['oeps'][oep_key]

    if isinstance(oep_value, dict):
        if not oep_value.get('applicable', True):
            pytest.xfail('OEP is not applicable')
            return

        if not oep_value['state']:
            pytest.xfail(oep_value['reason'])
    else:
        assert oep_value
