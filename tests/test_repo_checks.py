"""
(Incomplete) test suite for repo_checks.
"""
from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest

from edx_repo_tools.repo_checks import repo_checks


@pytest.fixture
def maintenance_label():
    """
    Quickly make a basic label to return via the API.
    """
    label = MagicMock()
    label.name = "maintenance"
    label.color = "ff9125"
    label.description = (
        "Routine upkeep necessary for the health of the platform"
    )

    return label


# Our list of expected labels, normally defined in labels.yaml.
labels_yaml = [
    {
        "name": "maintenance",
        "color": "ff9125",
        "description": "Routine upkeep necessary for the health of the platform",
    }
]


@patch.object(repo_checks.Labels, "labels", labels_yaml)
class TestLabelsCheck:
    def test_check_for_no_change(self, maintenance_label):
        api = MagicMock()
        api.issues.list_labels_for_repo.side_effect = [[maintenance_label], None]
        check_cls = repo_checks.Labels(api, "test_org", "test_repo")

        # Make sure that the check returns True, indicating that no changes need to be made.
        assert check_cls.check()[0]

    def test_addition(self, maintenance_label):
        api = MagicMock()
        api.issues.list_labels_for_repo.return_value = []
        check_cls = repo_checks.Labels(api, "test_org", "test_repo")

        # The check should be false because the maintenance label should be missing.
        assert check_cls.check()[0] == False

        check_cls.fix()
        assert api.issues.create_label.called

        call_args = api.issues.create_label.call_args
        expected_call = call(
            owner="test_org",
            repo="test_repo",
            name=maintenance_label.name,
            color=maintenance_label.color,
            description=maintenance_label.description,
        )
        assert call_args == expected_call
        assert not api.issues.update_label.called

    def test_update_label(self, maintenance_label):
        maintenance_label.name = ":+1: Ma.in-t 'e'n_a\"nce!\" :-1:"
        api = MagicMock()
        api.issues.list_labels_for_repo.side_effect = [[maintenance_label], None]

        check_cls = repo_checks.Labels(api, "test_org", "test_repo")

        assert check_cls.check()[0] == False
        check_cls.fix()

        call_args = api.issues.update_label.call_args
        expected_call = call(
            owner="test_org",
            repo="test_repo",
            name=maintenance_label.name,
            color=maintenance_label.color,
            new_name="maintenance",
            description=maintenance_label.description,
        )

        assert call_args == expected_call
        assert not api.issues.create_label.called
        assert api.issues.update_label.called
